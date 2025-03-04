def write_combined_binary(mif_low_file, mif_high_file, mif_16x32_file, output_file, target_size=81920):
    """
    Generates a combined binary file from split MIF files.

    Parameter order:
      - mif_low_file:  MIF for 32x64 Low section (written at offset 0xC000)
      - mif_high_file: MIF for 32x64 High section (written at offset 0x4000)
      - mif_16x32_file: MIF for 16x32 section which contains both normal and strikeout characters.
         - Normal entries at 0x0000
         - Strikeout entries starting at 0x2000 in the final binary

    The binary file is padded to exactly target_size bytes. We then compute a direct 16-bit sum
    of the first (target_size - 2) bytes (little-endian) and store that sum in the last 2 bytes,
    also little-endian.
    """
    import os

    # Offsets for the 32x64 sections:
    base_offsets = {
        "32x64 High": 0x4000,   # 32K region: 0x4000..0xBFFF
        "32x64 Low":  0xC000    # 32K region: 0xC000..0x13FFF
    }

    # For 16x32:
    #  - Normal characters at offset = 0x0000 + (index * 2)
    #  - Strikeout characters at offset = 0x2000 + (index * 2)

    ###########################################################################
    #                           MIF Loaders
    ###########################################################################
    def load_mif_data(file_path):
        """Loads 32x64 MIF data (addr, data_str)."""
        entries = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" not in line or not line.endswith(";"):
                    continue
                parts = line.split(":")
                address_str = parts[0].strip()
                data_str = parts[1].split(";")[0].strip()
                try:
                    addr = int(address_str, 16)
                except ValueError:
                    continue
                # Expect 4 hex digits
                if len(data_str) == 4 and all(c in "0123456789ABCDEFabcdef" for c in data_str):
                    entries.append((addr, data_str))
        return entries

    def load_mif_data_16x32(file_path):
        """
        Loads the 16x32 MIF, distinguishing normal vs. strikeout by comment.
        Normal entries => ("normal", index, data_str)
        Strikeout entries => ("strikeout", index, data_str)
        """
        entries = []
        mode = "normal"
        normal_count = 0
        strikeout_count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("--"):
                    if "strikeout" in line.lower():
                        mode = "strikeout"
                    continue
                if ":" not in line or not line.endswith(";"):
                    continue
                parts = line.split(":")
                data_str = parts[1].split(";")[0].strip()
                if len(data_str) == 4 and all(c in "0123456789ABCDEFabcdef" for c in data_str):
                    if mode == "normal":
                        entries.append(("normal", normal_count, data_str))
                        normal_count += 1
                    else:
                        entries.append(("strikeout", strikeout_count, data_str))
                        strikeout_count += 1
        return entries

    ###########################################################################
    #                  Load Each Section's MIF Data
    ###########################################################################
    data_32x64_low  = load_mif_data(mif_low_file)
    data_32x64_high = load_mif_data(mif_high_file)
    data_16x32      = load_mif_data_16x32(mif_16x32_file)

    print("16x32 entries:", len(data_16x32))
    print("32x64 High entries:", len(data_32x64_high))
    print("32x64 Low entries:", len(data_32x64_low))

    ###########################################################################
    #           1) Pre-fill the file to exactly target_size bytes
    ###########################################################################
    with open(output_file, "wb") as bin_file:
        bin_file.write(b"\x00" * target_size)

    ###########################################################################
    #           2) Write data into the first (target_size - 2) region
    ###########################################################################
    prefill_size = target_size - 2  # we reserve 2 bytes at the end for the checksum

    with open(output_file, "r+b") as bin_file:
        #
        # 16x32 section
        #
        for mode, index, data_str in data_16x32:
            if mode == "normal":
                offset = 0x0000 + (index * 2)
            else:  # "strikeout"
                offset = 0x2000 + (index * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(data_str))

        #
        # 32x64 High section
        #
        for addr, data_str in data_32x64_high:
            offset = base_offsets["32x64 High"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(data_str))

        #
        # 32x64 Low section
        #
        for addr, data_str in data_32x64_low:
            offset = base_offsets["32x64 Low"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(data_str))

    ###########################################################################
    #           3) Direct-Sum Checksum (Little-Endian)
    ###########################################################################
    def apply_direct_sum_checksum(file_path, data_size):
        """
        Sums all 16-bit little-endian words in the first data_size bytes
        and stores that sum in the last 2 bytes (little-endian).
        """
        with open(file_path, "rb+") as f:
            data = bytearray(f.read())

            sum16 = 0
            for i in range(0, data_size, 2):
                # Combine two bytes as little-endian
                word = data[i] | (data[i+1] << 8)
                sum16 = (sum16 + word) & 0xFFFF

            # Store sum16 in the last two bytes in little-endian
            data[-2] = (sum16 & 0xFF)
            data[-1] = ((sum16 >> 8) & 0xFF)

            f.seek(0)
            f.write(data)

        print(f"Direct-sum checksum 0x{sum16:04X} stored in last 2 bytes of '{file_path}'.")

    # Apply the direct-sum checksum to the first (target_size - 2) bytes
    apply_direct_sum_checksum(output_file, prefill_size)

    final_size = os.path.getsize(output_file)
    print(f"✅ Combined binary written to {output_file}")
    print(f"Total file size: {final_size} bytes (expected {target_size})")
