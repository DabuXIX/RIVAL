#define HDMI_INPUT 27
#define DP_INPUT   30

int current_input = HDMI_INPUT;  // Start on HDMI or pull from stored state

void handle_button_press(void) {
    int new_input = (current_input == HDMI_INPUT) ? DP_INPUT : HDMI_INPUT;

    // Tell the board to switch
    ecount_set_adjuster(adjInputSelect, new_input);

    // Check the board's response to see if it actually switched
    int input_changed = 0;

    for (int i = 0; i < 3; i++) {
        input_type = ecount_get_version();

        // Optional: small delay if needed
        // HAL_Delay(10);

        if (i == 0 && input_type != 0x80) {
            input_changed = 1;  // First response ≠ 0x80 → switch happened
        }
    }

    if (input_changed) {
        current_input = new_input;
    }
}
