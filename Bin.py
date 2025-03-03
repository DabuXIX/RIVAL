def write_combined_binary(mif_16x32, mif_32x64_high, mif_32x64_low, output_file, target_size=81920):
    """
    Generates a binary file from MIF output, ensuring all sections are correctly spaced:
    - 16x32 at 0x0000 (16K)
    - 32x64 High at 0x4000 (32K)
    - 32x64 Low at 0xC000 (32K)
    """

    def parse_mif(mif_file):
        """Extracts address-data pairs from a MIF file."""
        data_map = {}
        with open(mif_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" in line and line.endswith(";"):
                    parts = line.split(":")
                    address = int(parts[0].strip(), 16)
                    data = parts[1].split(";")[0].strip()
                    if len(data) == 4:  # Ensure 16-bit words
                        data_map[address] = bytes.fromhex(data)
        return data_map

    # Parse the MIFs
    data_16x32 = parse_mif(mif_16x32)
    data_32x64_high = parse_mif(mif_32x64_high)
    data_32x64_low = parse_mif(mif_32x64_low)

    # Expected section start offsets
    offsets = {
        "16x32": 0x0000,
        "32x64 High": 0x4000,
        "32x64 Low": 0xC000
    }

    # Open binary file for writing
    with open(output_file, "wb") as bin_file:
        # Ensure correct size with padding
        bin_file.write(b"\x00" * target_size)

        # Write 16x32 data at 0x0000
        for address, word in data_16x32.items():
            bin_file.seek(offsets["16x32"] + (address * 2))
            bin_file.write(word)

        # Write 32x64 High data at 0x4000
        for address, word in data_32x64_high.items():
            bin_file.seek(offsets["32x64 High"] + (address * 2))
            bin_file.write(word)

        # Write 32x64 Low data at 0xC000
        for address, word in data_32x64_low.items():
            bin_file.seek(offsets["32x64 Low"] + (address * 2))
            bin_file.write(word)

    print(f"✅ Binary file saved at {output_file} with correct section offsets!")
