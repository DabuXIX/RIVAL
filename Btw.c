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
