uint8_t ecount_get_version(void)
{
    // Prepare and send the version request packet
    uint8_t packet[5];
    packet[0] = ECOUNT_HEADER;
    packet[1] = ECOUNT_NODE;
    packet[2] = 0x12; // Get_Firmware_Version
    packet[3] = 0;
    packet[4] = checksum(&packet[1], 3);

    ecount_send(packet, 5);

    // Small delay to allow time for a response
    HAL_Delay(30);

    // Buffer to hold the incoming response
    uint8_t ecount_last_packet[15];
    uint8_t answer_byte_cnt = 0;

    // Parse message from cyclic buffer
    while ((rs_232_dm_tail != rs_232_dm_head) && (answer_byte_cnt < sizeof(ecount_last_packet)))
    {
        uint8_t byte = rs_232_dm_rx_buffer[rs_232_dm_tail];

        // Increment tail with wraparound
        rs_232_dm_tail = (rs_232_dm_tail + 1) % RS_232_DM_CYCBUFFLENGTH;

        // Deassert full flag now that we’ve read
        rs_232_dm_rx_buffer_full = 0;

        // Wait for Start-of-Header (0xBB) as the first valid byte
        if (answer_byte_cnt == 0 && byte != 0xBB)
            continue;

        // Store the valid byte
        ecount_last_packet[answer_byte_cnt++] = byte;
    }

    // If message complete, extract type byte
    if (answer_byte_cnt == sizeof(ecount_last_packet))
    {
        uint8_t input_type = ecount_last_packet[13];  // Assuming byte 13 holds the type
        return input_type;
    }

    // Return 0 or error indicator if parsing failed
    return 0;
}
