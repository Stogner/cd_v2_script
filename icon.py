from PIL import Image, ImageDraw


def crea_icona(size=64):
    """Icona di ConsoleDeck: un deck scuro con i pulsanti arancioni e la manopola del volume."""
    s = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((1 * s, 7 * s, 63 * s, 57 * s), radius=8 * s,
                        fill=(40, 40, 40, 255), outline=(200, 200, 200, 255), width=max(1, round(2 * s)))
    for riga in range(3):
        for col in range(3):
            x, y = (7 + col * 15) * s, (12 + riga * 15) * s
            d.rounded_rectangle((x, y, x + 11 * s, y + 11 * s), radius=2 * s, fill=(200, 120, 40, 255))
    d.ellipse((50 * s, 26 * s, 60 * s, 36 * s), outline=(200, 200, 200, 255), width=max(1, round(2 * s)))
    return img
