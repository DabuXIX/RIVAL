def write_combined_binary(mif_16x32_file, mif_32x64_high_file, mif_32x64_low_file, output_file, target_size=81920):
    """
    Generates a binary file with three sections written at fixed offsets:
      - 16x32 at 0x0000 (16K)
      - 32x64 High at 0x4000 (32K)
      - 32x64 Low at 0xC000 (32K)
    The file is padded to target_size bytes.
    """
    import os

    # Define base offsets for each section.
    base_offsets = {
        "16x32": 0x0000,
        "32x64 High": 0x4000,
        "32x64 Low": 0xC000
    }

    # A helper function that processes one MIF file and writes its data.
    def write_section(bin_file, mif_file, base_offset):
        with open(mif_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Look for lines that look like: "XXXX : YYYY;"
                if ":" in line and line.endswith(";"):
                    parts = line.split(":")
                    try:
                        addr = int(parts[0].strip(), 16)
                    except ValueError:
                        continue
                    data_str = parts[1].split(";")[0].strip()
                    # Expecting a 16-bit word (4 hex digits)
                    if len(data_str) == 4 and all(c in "0123456789ABCDEFabcdef" for c in data_str):
                        offset = base_offset + (addr * 2)
                        bin_file.seek(offset)
                        bin_file.write(bytes.fromhex(data_str))

    # Create and pre-pad the binary file.
    with open(output_file, "wb") as bin_file:
        # Pre-fill the file with zeros to the target size.
        bin_file.write(b"\x00" * target_size)

        # Write each section at its base offset.
        write_section(bin_file, mif_16x32_file, base_offsets["16x32"])
        write_section(bin_file, mif_32x64_high_file, base_offsets["32x64 High"])
        write_section(bin_file, mif_32x64_low_file, base_offsets["32x64 Low"])

    print(f"✅ Binary file saved at {output_file} with sections written at proper offsets.")
