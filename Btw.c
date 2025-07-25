for (int i = 0; i < RS_232_DM_RXBUFLENGTH; i++) {
    uint16_t index = (rs_232_dm_tail + i) % RS_232_DM_RXBUFLENGTH;

    if (rs_232_dm_rx_buffer[index] == 0xBB &&
        rs_232_dm_rx_buffer[(index + 2) % RS_232_DM_RXBUFLENGTH] == 0x12) {

        // Valid header found, copy packet
        for (int j = 0; j < 15; j++) {
            ecount_last_packet[j] = rs_232_dm_rx_buffer[(index + j) % RS_232_DM_RXBUFLENGTH];
        }

        uint8_t input_type = ecount_last_packet[13];

        memset(ecount_last_packet, 0, sizeof(ecount_last_packet));

        // Advance tail
        rs_232_dm_tail = (index + 15) % RS_232_DM_RXBUFLENGTH;
        rs_232_dm_rx_buffer_full = 0;

        return input_type;
    }
}




uint8_t ecount_get_version(void) {
    for (int i = 0; i < RS_232_DM_RXBUFLENGTH; i++) {
        uint16_t index = (rs_232_dm_tail + i) % RS_232_DM_RXBUFLENGTH;

        // Match header: Byte 0 = 0xBB, Byte 2 = 0x12
        if (rs_232_dm_rx_buffer[index] == 0xBB &&
            rs_232_dm_rx_buffer[(index + 2) % RS_232_DM_RXBUFLENGTH] == 0x12) {

            // Check if full 15-byte packet is available in buffer
            uint16_t next_head = (index + 15) % RS_232_DM_RXBUFLENGTH;
            bool enough_data;

            if (rx_head >= index) {
                enough_data = (next_head <= rx_head);
            } else {
                enough_data = !(next_head > rx_head && next_head < index);
            }

            if (!enough_data) {
                return 0xFF; // Not enough new data yet
            }

            // Copy packet into ecount_last_packet
            for (int j = 0; j < 15; j++) {
                ecount_last_packet[j] = rs_232_dm_rx_buffer[(index + j) % RS_232_DM_RXBUFLENGTH];
            }

            uint8_t input_type = ecount_last_packet[13];

            // Advance tail after successful parse
            rs_232_dm_tail = (index + 15) % RS_232_DM_RXBUFLENGTH;
            rs_232_dm_rx_buffer_full = 0;

            return input_type;
        }
    }

    return 0xFF; // No valid packet found
}
