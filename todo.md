Testing (in Game Mode now)                                                                                                                                                                                                                                
                                                            
  1. Open Decky menu → verify AudioForge appears                                                                                                                                                                                                            
  2. Toggle DSP effects on/off → verify audio changes                                                                                                                                                                                                     
  3. Test individual effects (EQ, reverb, compressor, bass boost, etc.)
  4. Test per-game profiles if supported
  5. Plug/unplug HDMI → verify audio switches automatically
  6. Reboot → verify audio works on cold boot without manual intervention

  GitHub Repo Setup

  1. Initialize git repo in /home/deck/code/AudioForge/
  2. Create .gitignore (node_modules, build artifacts, .flatpak-builder, build-dir, repo)
  3. Initial commit with all source files
  4. Create GitHub repo audioforge/AudioForge
  5. Push to remote

  GitHub Release

  1. Tag the release (e.g., v0.1.0)
  2. Create release with gh release create
  3. Attach bin/jamesdsp.flatpak as release asset
  4. Attach packaged plugin zip if needed for Decky store

  README

  1. What AudioForge does (patched JamesDSP for SteamOS)
  2. The loopback bug it fixes
  3. Install instructions (Decky plugin install)
  4. Build instructions (flatpak + frontend)
  5. Credits (JDSP4Linux, DeckSP)

  Upstream Consideration

  1. Open issue/PR on JDSP4Linux describing the loopback bug
  2. Propose the PW_KEY_APP_ID check fix
  3. If accepted, AudioForge could eventually just use upstream JamesDSP

  Want to tackle any of these now or wait until after testing?
