import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  hcp_name: '',
  interaction_type: '',
  date: '',
  time: '',
  attendees: [],
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  sentiment: '',
  outcomes: '',
  follow_up_actions: '',
  suggested_follow_ups: [],
  compliance_flag: 'clear',
  compliance_rationale: '',
};

export const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    setInteraction: (state, action) => {
      return { ...state, ...action.payload };
    },
    patchInteraction: (state, action) => {
      Object.assign(state, action.payload);
    },
    clearInteraction: () => initialState,
  },
});

export const { setInteraction, patchInteraction, clearInteraction } = interactionSlice.actions;

export default interactionSlice.reducer;
