import qrcode
from PIL import Image
from qrcode.constants import ERROR_CORRECT_H

# Your website
url = "https://inktenebris.github.io"
# Create QR
qr = qrcode.QRCode(
    version=5,
    error_correction=ERROR_CORRECT_H,  # High error correction
    box_size=20,
    border=2,
)
qr.add_data(url)
qr.make(fit=True)
# White QR on black background
qr_img = qr.make_image(fill_color="white", back_color="black")
qr_img = qr_img.convert("RGB")
# Save
qr_img.save("inktenebris_qr_logo.png")
print("QR with logo generated!")
