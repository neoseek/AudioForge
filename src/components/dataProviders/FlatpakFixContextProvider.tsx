import { useState, FC17 } from 'react';
import { FlatpakFixContext } from '../../contexts/contexts';
import { PLUGIN_NAME } from '../../defines/constants';
import { FlatpakFixState } from '../../types/types';

export const FixFlatpakDescriptions = {
    default: `${PLUGIN_NAME} encountered an error with the JamesDSP flatpak installation. You can try to run this fix to automatically repair it. After the process is complete the plugin must be reloaded. An active internet connection is required.`,
    done: `The repair process completed. Reload ${PLUGIN_NAME} from the Decky plugin menu. An active internet connection is required during the reload process.`
};

export const FlatpakFixProvider: FC17<{}> = ({ children }) => {
    const [state, setState] = useState(FlatpakFixState.Default);
    const [description, setDescription] = useState(FixFlatpakDescriptions.default);

    return (
        <FlatpakFixContext.Provider value={{ state, setState, description, setDescription }}>
            {children}
        </FlatpakFixContext.Provider>
    );
};