import asyncio
import json
import os
import re
import subprocess
import time
from EelParser import EELParser
from ddc import VdcDbHandler
from extendedsettings import ExtendedSettings
from settings import SettingsManager

from env import env
from jdspproxy import JdspProxy
from utils import SettingDef, compare_versions, flatpak_CMD, get_xauthority, wrap_error, restart_wireplumber, set_alsa_master_volume
from volume_forwarder import VolumeForwarder

import decky

APPLICATION_ID = "org.audioforge.jamesdsp"
JDSP_LOG_DIR =  os.path.join(decky.DECKY_PLUGIN_LOG_DIR, 'jdsp')
JDSP_LOG = os.path.join(JDSP_LOG_DIR, 'jdsp.log')
JDSP_FLATPAK_BUNDLE = os.path.join(decky.DECKY_PLUGIN_DIR, 'bin', 'jamesdsp.flatpak')
JDSP_MIN_VER = '2.7.0'

log = decky.logger

"""
------------------------------------------------------------------------------------------------------------------------------
Setting definitions
"""
class Setting(SettingDef):
    ENABLE_IN_DESKTOP = 'enableInDesktop'
    DSP_PAGE_ORDER = 'dspPageOrder'
    DISABLE_PROFILE_TOAST = 'disableProfileToasts'
    RESTART_PIPELINE_ON_DEVICE = 'restartPipelineOnDeviceDetect'

    class Defaults:
        ENABLE_IN_DESKTOP = True
        RESTART_PIPELINE_ON_DEVICE = []
        

class ProfileSetting(SettingDef):
    MANUAL_PRESET = 'manualPreset'
    USE_MANUAL = 'useManual'
    WATCHED_APPS = 'watchedApps'

    class Defaults:
        USE_MANUAL = False
        WATCHED_APPS = {}
"""
------------------------------------------------------------------------------------------------------------------------------
"""

class OnDisk:
    @classmethod
    def init_user(cls, user_id, account_name):
        cls.user = cls.User(user_id, account_name)
    
    class User:
        def __init__(self, user_id, account_name):
            dir = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, f'{account_name}_{user_id}')
            if not os.path.exists(dir):
                os.makedirs(dir)
            self.settings = ExtendedSettings(name="settings", settings_directory=dir)
            self.profiles = ExtendedSettings(name="profiles-data", settings_directory=dir)
            self.vdc_db_selections = ExtendedSettings(name='vdc-db-selections', settings_directory=dir)
            self.eel_cache = ExtendedSettings(name='eel-parameters', settings_directory=dir)
    
    class Shared:
        def __init__(self):
            self.user_map = SettingsManager(name='user-map', settings_directory=decky.DECKY_PLUGIN_SETTINGS_DIR)
    
    shared = Shared()

class Plugin:
    jdsp: JdspProxy = None
    jdsp_install_state = 'installing'  # 'installing', 'ready', 'failed'
    _install_complete: asyncio.Event = None
    _volume_forwarder: VolumeForwarder = None
    current_preset = ''
    vdc_handler: VdcDbHandler
    eel_parser: EELParser

    async def _main(self):
        log.info('Starting plugin backend...')
        self._remove_legacy_settings()
        if not os.path.exists(JDSP_LOG_DIR):
            os.makedirs(JDSP_LOG_DIR)

        self.jdsp = JdspProxy(APPLICATION_ID, log)

        self._install_complete = asyncio.Event()
        self.jdsp_install_state = 'installing'
        # Run blocking install in background thread so frontend RPC calls aren't blocked
        asyncio.ensure_future(self._run_install_async())

    async def _run_install_async(self):
        try:
            result = await asyncio.to_thread(self._handle_jdsp_install)
            if result:
                self.jdsp_install_state = 'ready'
                log.info('Plugin ready')
            else:
                self.jdsp_install_state = 'failed'
                log.error('Problem with JamesDSP installation')
        except Exception as e:
            self.jdsp_install_state = 'failed'
            log.error(f'Install error: {e}')
        finally:
            self._install_complete.set()

    async def _uninstall(self):
        log.info('Uninstalling plugin...')

        flatpak_CMD(['kill', APPLICATION_ID], noCheck=True)
        try: 
            log.info('Uninstalling JamesDSP...')
            flatpak_CMD(['--user', '-y', 'uninstall', APPLICATION_ID])
            log.info("JamesDSP uninstalled successfully")

        except subprocess.CalledProcessError as e:
            log.error('Problem uninstalling JamesDSP')
            log.error(e.stderr)

    async def _unload(self):
        log.info('Unloading plugin...')
        await self._stop_volume_forwarder()
        flatpak_CMD(['kill', APPLICATION_ID], noCheck=True)
        
    def _init_defaults(self):
        OnDisk.user.settings.setDefaults(Setting.defaults())
        OnDisk.user.profiles.setDefaults(ProfileSetting.defaults())    
        
    def _get_installed_jdsp_version(self):
        """Return the installed JamesDSP version string, or '' if not found."""
        try:
            res = flatpak_CMD(['list', '--user', '--app', '--columns=application,version'])
            for line in res.stdout.split('\n'):
                if line.startswith(APPLICATION_ID):
                    return line.split()[1]
        except subprocess.CalledProcessError:
            pass
        return ''

    def _handle_jdsp_install(self):
        log.info('Checking for patched JamesDSP installation...')
        try:
            installed_version = self._get_installed_jdsp_version()

            if installed_version != '':
                log.info(f'JamesDSP version {installed_version} is installed')
                if compare_versions(installed_version, JDSP_MIN_VER) >= 0:
                    return True
                else:
                    log.info(f'Minimum version is {JDSP_MIN_VER}')

            if not os.path.exists(JDSP_FLATPAK_BUNDLE):
                log.error(f'Flatpak bundle not found at {JDSP_FLATPAK_BUNDLE}')
                return False

            log.info('Installing patched JamesDSP from flatpak bundle...')
            installRes = flatpak_CMD(['--user', '-y', 'install', '--or-update', JDSP_FLATPAK_BUNDLE])
            log.info(installRes.stdout)
            log.info('Patched JamesDSP installed successfully')

            return True

        except subprocess.CalledProcessError as e:
            if 'already installed' in (e.stderr or ''):
                # A previous install may still be in progress or left a partial state.
                # Wait for it to finish, then re-check the version.
                log.info('Install reported "already installed" — waiting for any in-progress install to complete...')
                for attempt in range(6):
                    time.sleep(5)
                    installed_version = self._get_installed_jdsp_version()
                    if installed_version != '':
                        log.info(f'JamesDSP version {installed_version} now detected')
                        if compare_versions(installed_version, JDSP_MIN_VER) >= 0:
                            return True
                        break

                # Still broken — remove and reinstall cleanly
                log.info('Detected broken/partial JamesDSP install, removing and reinstalling...')
                try:
                    flatpak_CMD(['--user', '-y', 'uninstall', APPLICATION_ID], noCheck=True)
                    installRes = flatpak_CMD(['--user', '-y', 'install', '--or-update', JDSP_FLATPAK_BUNDLE])
                    log.info(installRes.stdout)
                    log.info('Patched JamesDSP reinstalled successfully')
                    return True
                except subprocess.CalledProcessError as e2:
                    log.error(f'Failed to reinstall after cleanup: {e2.stderr}')
                    return False
            log.error(e.stderr)
            return False
        
    def _clean_eel_cache(self):
        deleted = False
        for path in list(OnDisk.user.eel_cache.settings.keys()):
            if not os.path.exists(path):
                del OnDisk.user.eel_cache.settings[path]
                deleted = True
        if deleted: OnDisk.user.eel_cache.commit()

    def _update_eel_cache_and_reload_jdsp(self):
        OnDisk.user.eel_cache.setSetting(self.eel_parser.path, self.eel_parser.cache)
        self.jdsp.set_and_commit('liveprog_file', "")
        self.jdsp.set_and_commit('liveprog_file', self.eel_parser.path)

    def _get_jdsp_all_and_apply_vdc_from_db(self, preset_name):
        vdc_path = self.jdsp.get('ddc_file').get('jdsp_result', '').strip()
        try:
            if self.vdc_handler.is_proxy_path(vdc_path): # using database proxy file
                self.jdsp.set_and_commit('ddc_file', '/home/deck/.var/app/org.audioforge.jamesdsp/config/jamesdsp/vdc') # setting this empty or any random string doesnt actually clear the effect for some reason, but this works, so set it first
                self.jdsp.set_and_commit('ddc_file', '')
    
                selected_vdc_id = OnDisk.user.vdc_db_selections.getSetting(preset_name)
                if self.vdc_handler.set_and_commit(selected_vdc_id): # vdc id is in database. if this is false empty string is set for the jdsp param
                    self.jdsp.set_and_commit('ddc_file', self.vdc_handler._jdsp_proxy_path)
                else: 
                    OnDisk.user.vdc_db_selections.removeSetting(preset_name)
        except Exception as e:
            return wrap_error(e)
        return self.jdsp.get_all()
    
    # changes from 1.0.0
    def _rename_legacy_presets(self, user_id):
        presets_res = self.jdsp.get_presets()
        if JdspProxy.has_error(presets_res):
            log.info(f'Problem getting presets when trying to update legacy: {JdspProxy.unwrap(presets_res)}')
            
        presets = JdspProxy.unwrap(presets_res).splitlines()
        regex = re.compile(r"^(decksp).(user|game):(.+)$")
        
        for _, preset in enumerate(presets):
            match = regex.search(preset)
            if match:
                decksp_prefix, profile_type, profile_id = match.groups()
                if profile_type == 'user': profile_type = 'custom'
                rename_res = self.jdsp.rename_preset(preset, f'{decksp_prefix}.{user_id}.{profile_type}:{profile_id}')
                if JdspProxy.has_error(rename_res):
                    log.info(f'Problem renaming legacy jdsp preset {preset}: {JdspProxy.unwrap(rename_res)}')
    
    # changes from 1.0.0
    def _remove_legacy_settings(self):
        legacy_settings_path = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, 'settings.json')
        if os.path.exists(legacy_settings_path):
            try:
                os.remove(legacy_settings_path) 
            except Exception as e:    
                log.error(f'Error trying to remove legacy settings: {e}')
        
    """
    ===================================================================================================================================
    FRONTEND CALLED METHODS
    ===================================================================================================================================

    
    ------------------------------------------
    General plugin methods
    ------------------------------------------
    return any value or dictionary with an 'error' property

    Annotation: 'general-frontend-call'
    """

    # general-frontend-call
    async def get_install_status(self):
        return self.jdsp_install_state

    # general-frontend-call
    async def start_jdsp(self):
        # Wait for install to complete if still in progress
        if self.jdsp_install_state == 'installing':
            await self._install_complete.wait()
        if self.jdsp_install_state != 'ready':
            return False
        
        log.info(f'Starting JamesDSP... See process logs at {JDSP_LOG}')
        
        xauth = get_xauthority()
        new_env = env.copy()
        # run without gui in Game Mode (no X11 display available)
        new_env['QT_QPA_PLATFORM'] = 'offscreen'
        if xauth: new_env['XAUTHORITY'] = xauth
        flatpak_CMD(['kill', APPLICATION_ID], noCheck=True)
        with open(JDSP_LOG, "w") as jdsp_log:
            subprocess.Popen(f'flatpak --user run {APPLICATION_ID} --tray', stdout=jdsp_log, stderr=jdsp_log, shell=True, env=new_env, universal_newlines=True)
        set_alsa_master_volume()
        await self._start_volume_forwarder()
        return True # assume process has started ignoring errors so that the frontend doesn't hang. the jdsp process errors will be logged in its own file

    async def _start_volume_forwarder(self):
        if self._volume_forwarder:
            await self._volume_forwarder.stop()
        self._volume_forwarder = VolumeForwarder()
        await self._volume_forwarder.start()

    async def _stop_volume_forwarder(self):
        if self._volume_forwarder:
            await self._volume_forwarder.stop()
            self._volume_forwarder = None

    # general-frontend-call
    async def kill_jdsp(self):
        log.info('Killing JamesDSP')
        await self._stop_volume_forwarder()
        flatpak_CMD(['kill', APPLICATION_ID], noCheck=True)
        
    async def force_pw_relink(self):
        timeout = 5
        log.info('Attempting to relink pipewire')

        try:
            jdspRunning = APPLICATION_ID in flatpak_CMD(["ps", "--columns=application"]).stdout
        except Exception:
            msg = "Failed to detect if JamesDSP is running before attempting to restart wireplumber"
            log.error(msg)
            return wrap_error(msg)
        try:
            if jdspRunning:
                log.info('Killing JamesDSP')
                flatpak_CMD(['kill', APPLICATION_ID])
        except Exception:
            msg = "Failed to kill JamesDSP before attempting to restart wireplumber"
            log.error(msg)
            return wrap_error(msg)
    
        try:
            log.info('Restarting wireplumber')
            await restart_wireplumber(timeout, 2)
            log.info('Wireplumber restarted')
            await self.start_jdsp()
        except Exception as e:
            log.error(str(e))
            return wrap_error(e)

    # general-frontend-call
    async def init_user(self, userId, accountName, personaName):
        OnDisk.init_user(userId, accountName)
        OnDisk.shared.user_map.setSetting(userId, [accountName, personaName])
        self._init_defaults()
        self._clean_eel_cache()
        self.vdc_handler = VdcDbHandler(os.path.join(decky.DECKY_PLUGIN_DIR, 'resources', 'DDCData.json'))
        log.info(f'User {accountName} ({userId}) logged in')
        return OnDisk.user.settings.settings
    
    # general-frontend-call
    async def set_settings(self, settings):
        OnDisk.user.settings.setMultipleSettings(settings)

    # general-frontend-call
    async def flatpak_repair(self):
        try:
            flatpak_CMD(['repair', '--user'])
            return
        except subprocess.CalledProcessError as e:
            log.error(e.stderr)
            return wrap_error(e.stderr)

    # general-frontend-call
    async def set_app_watch(self, appId, watch):
        watched = OnDisk.user.profiles.getSetting(ProfileSetting.WATCHED_APPS)
        watched[appId] = watch
        OnDisk.user.profiles.setSetting(ProfileSetting.WATCHED_APPS, watched)

    # general-frontend-call
    async def init_profiles(self, globalPreset, currentUser):
        if OnDisk.user.profiles.getSetting(ProfileSetting.MANUAL_PRESET) is None:
            OnDisk.user.profiles.setSetting(ProfileSetting.MANUAL_PRESET, globalPreset)

        self._rename_legacy_presets(currentUser) # changes from 1.0.0
        presets = self.jdsp.get_presets()
        if JdspProxy.has_error(presets):
            return wrap_error(presets)

        return { 
            'manualPreset': OnDisk.user.profiles.getSetting(ProfileSetting.MANUAL_PRESET), 
            'allPresets': presets['jdsp_result'], 
            'watchedGames': OnDisk.user.profiles.getSetting(ProfileSetting.WATCHED_APPS),
            'manuallyApply': OnDisk.user.profiles.getSetting(ProfileSetting.USE_MANUAL) 
        }

    # general-frontend-call
    async def set_manually_apply_profiles(self, useManual):
        OnDisk.user.profiles.settings[ProfileSetting.USE_MANUAL] = useManual
    
    # general-frontend-call
    async def get_eel_params_and_desc(self, path, profileId):
        if path == '': 
            return { 'description': '', 'parameters': [] }
        self.eel_parser = EELParser(path, OnDisk.user.eel_cache.getSetting(path, {}), profileId)
        self._update_eel_cache_and_reload_jdsp()
        return { 'description': self.eel_parser.description, 'parameters': self.eel_parser.parameters }
    
    # general-frontend-call
    async def set_eel_param(self, paramName, value):
        self.eel_parser.set_and_commit(paramName, value)
        self._update_eel_cache_and_reload_jdsp()
    
    # general-frontend-call
    async def reset_eel_params(self):
        self.eel_parser.reset_to_defaults()
        self._update_eel_cache_and_reload_jdsp()
    
    # general-frontend-call
    async def set_vdc_db_selection(self, vdcId, presetName): 
        jdsp_error = JdspProxy.has_error(await self.set_jdsp_param('ddc_file', ''))
        if jdsp_error: return wrap_error('Failed setting jdsp ddc_file empty for reload')
        if self.vdc_handler.set_and_commit(vdcId):
            jdsp_error = JdspProxy.has_error(await self.set_jdsp_param('ddc_file', self.vdc_handler._jdsp_proxy_path))
            if jdsp_error: return wrap_error('Failed reloading jdsp ddc_file')
            OnDisk.user.vdc_db_selections.setSetting(presetName, vdcId)
        else: 
            OnDisk.user.vdc_db_selections.removeSetting(presetName)
            return wrap_error(f'Could not find vdc id: {vdcId} in the database')
    
    # general-frontend-call
    async def get_vdc_db_selections(self):
        return OnDisk.user.vdc_db_selections.settings
        
    # general-frontend-call
    async def get_static_data(self):
        return { 'vdcDb': self.vdc_handler.get_frontend_db(), 'userMap': OnDisk.shared.user_map.settings }
    
    """
    ------------------------------------------
    JDSP specific methods
    ------------------------------------------
    return a JamesDSP cli result in a dictionary in the format of either...
    { 'jdsp_result': str } or { 'jdsp_error': str }

    Annotation: 'jdsp-frontend-call'
    """

    # jdsp-frontend-call
    async def set_jdsp_param(self, parameter, value):
        res = self.jdsp.set_and_commit(parameter, value)
        if not JdspProxy.has_error(res):
            self.jdsp.save_preset(self.current_preset)
        return res
    
    # jdsp-frontend-call
    async def set_jdsp_params(self, values):
        for parameter, value in values:
            res = self.jdsp.set_and_commit(parameter, value)
            if JdspProxy.has_error(res):
                return res
    
        self.jdsp.save_preset(self.current_preset)
        return JdspProxy.wrap_success_result('')

    # jdsp-frontend-call
    async def get_all_jdsp_param(self):
        return self._get_jdsp_all_and_apply_vdc_from_db(self.current_preset)

    # jdsp-frontend-call
    async def set_jdsp_defaults(self, defaultPreset):
        loadres = self.jdsp.load_preset(defaultPreset)                        # load the default preset settings
        if JdspProxy.has_error(loadres): return loadres
        saveres = self.jdsp.save_preset(self.current_preset)     # save the current preset with current settings
        if JdspProxy.has_error(saveres): return saveres
        return self.jdsp.get_all()

    # jdsp-frontend-call
    async def new_jdsp_preset(self, presetName, fromPresetName = None):
        if fromPresetName is not None: 
            loadres = self.jdsp.load_preset(fromPresetName)                   # load preset settings to copy
            if JdspProxy.has_error(loadres): return loadres
            saveres = self.jdsp.save_preset(presetName)                       # save the new preset with current settings
            if JdspProxy.has_error(saveres): return saveres
            return self.jdsp.load_preset(self.current_preset)    # reload the previous preset settings
        else: 
            return self.jdsp.save_preset(presetName)

    # jdsp-frontend-call
    async def delete_jdsp_preset(self, presetName):
        OnDisk.user.vdc_db_selections.removeSetting(presetName)
        return self.jdsp.delete_preset(presetName)

    # jdsp-frontend-call
    async def set_profile(self, presetName, isManual):
        if isManual:
            OnDisk.user.profiles.settings[ProfileSetting.MANUAL_PRESET] = presetName
        res = self.jdsp.load_preset(presetName)
        if JdspProxy.has_error(res): return res
        
        self.current_preset = presetName
        OnDisk.user.profiles.commit()
        return self._get_jdsp_all_and_apply_vdc_from_db(presetName)
    
    # jdsp-frontend-call
    async def create_default_jdsp_preset(self, defaultName):
        conf_file = os.path.expanduser(f'~/.var/app/{APPLICATION_ID}/config/jamesdsp/audio.conf')
        if os.path.exists(conf_file):
            try:
                os.remove(conf_file) # clear existing settings to ensure defaults    
            except Exception as e:    
                log.error(f'Error deleting audio.conf when trying to create default preset: {e}')
                raise e
        
        log.info('Creating default preset')
        return self.jdsp.save_preset(defaultName)

    """
    ===================================================================================================================================
    """