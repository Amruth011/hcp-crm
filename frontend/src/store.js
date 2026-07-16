import { configureStore } from '@reduxjs/toolkit';
import interactionReducer from './features/interactionSlice';

export const store = configureStore({
  reducer: {
    interaction: interactionReducer,
  },
});
