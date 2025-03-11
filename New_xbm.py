def generate_xbm_data(ttf_path, char_list, forced_height, max_width, canvas_width, canvas_height,
                      threshold_value=128, padding_top=0, padding_bottom=0):
    """
    Generates XBM data for characters, ensuring proper alignment within grids,
    narrow character handling, and padding.
    """
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    font_size = forced_height * 2
    font = ImageFont.truetype(ttf_path, font_size)
    all_xbm_data = {}

    punctuation_set = {',', '.'}
    punctuation_scale = 0.25
    narrow_chars = {"I"}
    narrow_char_scale = 0.5

    # For 32x64, use fixed grid dimensions
    grid_width = 17 if canvas_width == 32 and canvas_height == 64 else canvas_width
    grid_height = 39 if canvas_width == 32 and canvas_height == 64 else canvas_height

    for char in char_list:
        try:
            if char == " ":
                xbm_data = [
                    [0x00 for _ in range(canvas_width // 8)]  # Empty grid for space
                    for _ in range(canvas_height)
                ]
                all_xbm_data[char] = xbm_data
                continue

            (width, height), (offset_x, offset_y) = font.font.getsize(char)
            if width == 0 or height == 0:
                continue

            image = Image.new('L', (width, height), 0)
            draw = ImageDraw.Draw(image)
            draw.text((-offset_x, -offset_y), char, font=font, fill=255)

            # Set target height and scaling based on character type
            if char in punctuation_set:
                target_height = int(forced_height * punctuation_scale)
                aspect_ratio = width / height
                scaled_width = min(int(target_height * aspect_ratio), max_width)
            elif char in narrow_chars:
                target_height = forced_height
                aspect_ratio = width / height
                scaled_width = min(int(target_height * aspect_ratio * narrow_char_scale), max_width)
            else:
                target_height = forced_height
                aspect_ratio = width / height
                scaled_width = min(int(target_height * aspect_ratio), max_width)

            img_resized = image.resize((scaled_width, target_height), Image.Resampling.LANCZOS)
            binary_array = (np.array(img_resized) > threshold_value).astype(np.uint8)

            padded_array = np.zeros((canvas_height, canvas_width), dtype=np.uint8)

            if canvas_width == 32 and canvas_height == 64:
                # For the 32x64 grid, use fixed grid dimensions.
                if char in punctuation_set:
                    # Align punctuation to the bottom of the grid
                    vertical_offset = grid_height - binary_array.shape[0]
                else:
                    vertical_offset = max((grid_height - binary_array.shape[0]) // 2, 0)
                horizontal_offset = max((grid_width - binary_array.shape[1]) // 2, 0)
                padded_array[vertical_offset:vertical_offset + binary_array.shape[0],
                             horizontal_offset:horizontal_offset + binary_array.shape[1]] = binary_array
            else:
                if char in punctuation_set:
                    # Align punctuation to the bottom of the canvas
                    vertical_start = canvas_height - target_height - padding_bottom
                else:
                    vertical_start = padding_top
                horizontal_padding = (canvas_width - scaled_width) // 2
                padded_array[vertical_start:vertical_start + target_height,
                             horizontal_padding:horizontal_padding + scaled_width] = binary_array

            # Convert each row of the padded array into bytes, reversing bit order as needed.
            xbm_data = []
            for row in padded_array:
                row_bytes = []
                for byte_index in range(0, canvas_width, 8):
                    byte = 0
                    for bit_index in range(8):
                        col = byte_index + bit_index
                        if col < canvas_width and row[col]:
                            byte |= (1 << (7 - bit_index))
                    row_bytes.append(reverse_bits(byte))
                xbm_data.append(row_bytes)

            all_xbm_data[char] = xbm_data

        except Exception as e:
            print(f"Warning: Unable to process character '{char}'. Reason: {e}")

    return all_xbm_data
