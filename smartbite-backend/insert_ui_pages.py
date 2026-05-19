"""
Insert UI screenshot pages into prj_report_SmartBite_corrected (1).pdf
after Chapter 4 (Implementation, page index 32) and before Chapter 5 (Results).
"""

import fitz
import os
from PIL import Image as PILImage

PDF_PATH = r"c:\Users\Gaurang Simlionics\Desktop\Pricing Project\smartbite-backend\prj_report_SmartBite_corrected (1).pdf"
ASSETS_DIR = r"c:\Users\Gaurang Simlionics\Desktop\Pricing Project\smartbite-backend\assets"

IMAGES = [
    ("WhatsApp Image 2026-04-30 at 9.31.47 AM.jpeg",
     "Fig. 4.1: SmartBite Home Page — Hero section with food photography and Explore Restaurants call-to-action."),
    ("WhatsApp Image 2026-04-30 at 9.31.48 AM.jpeg",
     "Fig. 4.2: Home Page Features — Fast Delivery (under 30 min), Top Restaurants, and Easy Payments value cards."),
    ("WhatsApp Image 2026-04-30 at 9.31.49 AM.jpeg",
     "Fig. 4.3: How SmartBite Works — Three-step ordering flow: Browse Restaurants, Add to Cart, Fast Delivery."),
    ("WhatsApp Image 2026-04-30 at 9.31.50 AM.jpeg",
     "Fig. 4.4: Restaurants Listing — Search bar, cuisine filter, top-rated toggle, and restaurant cards with ratings and delivery time."),
    ("WhatsApp Image 2026-04-30 at 9.31.50 AM (1).jpeg",
     "Fig. 4.5: Restaurant Detail Page (Subway) — Menu grid with food images, item names, prices, and Add to Cart buttons."),
    ("WhatsApp Image 2026-04-30 at 9.31.51 AM.jpeg",
     "Fig. 4.6: Shopping Cart — Itemised order, quantity controls, dynamic pricing breakdown (FREE delivery via batching), Grand Total, and Checkout."),
    ("WhatsApp Image 2026-04-30 at 9.31.52 AM.jpeg",
     "Fig. 4.7: Payment Method Selection — Cash on Delivery, Credit/Debit Card, and UPI options."),
    ("WhatsApp Image 2026-04-30 at 9.31.52 AM (1).jpeg",
     "Fig. 4.8: Card Payment Form — Secure entry of card number, expiry date, CVV, and cardholder name."),
    ("WhatsApp Image 2026-04-30 at 9.31.53 AM.jpeg",
     "Fig. 4.9: Order Confirmation — Subtotal Rs.550, Delivery FREE (batch discount), Taxes Rs.28, Total Paid Rs.578 (SmartBite billing engine)."),
    ("WhatsApp Image 2026-04-30 at 9.31.53 AM (1).jpeg",
     "Fig. 4.10: User Account Page — Profile Details, Delivery Preferences, Current/Past Orders, and App Settings."),
]

# Insert new pages after PDF page index 32 (Chapter 4 last page, shows content page 32)
INSERT_AFTER = 32

PAGE_W = 596.04
PAGE_H = 842.52
MARGIN_X = 56.0
MARGIN_TOP_CONTENT = 68.0   # where content starts after header
MARGIN_BOT = 52.0
CONTENT_W = PAGE_W - 2 * MARGIN_X       # ~484 pt
CONTENT_H = PAGE_H - MARGIN_TOP_CONTENT - MARGIN_BOT  # ~722 pt


def draw_header(page, page_num: int):
    """Reproduce the standard report page header."""
    y1 = 20.0
    page.insert_text((MARGIN_X, y1),
                     "Delivery Optimization Algorithm",
                     fontname="helv", fontsize=9, color=(0, 0, 0))
    label = "PICT,Pune"
    lw = fitz.get_text_length(label, fontname="helv", fontsize=9)
    page.insert_text((PAGE_W - MARGIN_X - lw, y1),
                     label, fontname="helv", fontsize=9, color=(0, 0, 0))

    y2 = 33.0
    page.insert_text((MARGIN_X, y2),
                     "Dept. of Information Technology",
                     fontname="helv", fontsize=9, color=(0, 0, 0))

    y3 = 46.0
    pn = str(page_num)
    pw = fitz.get_text_length(pn, fontname="helv", fontsize=9)
    page.insert_text(((PAGE_W - pw) / 2, y3),
                     pn, fontname="helv", fontsize=9, color=(0, 0, 0))

    # Horizontal rule
    page.draw_line((MARGIN_X, 53.0), (PAGE_W - MARGIN_X, 53.0),
                   color=(0, 0, 0), width=0.5)


def place_screenshot(page, img_path: str, caption: str,
                     x: float, y: float, slot_w: float, slot_h: float):
    """Draw one screenshot + caption inside the given slot; return height used."""
    CAP_H = 22.0
    GAP   = 6.0
    max_img_h = slot_h - CAP_H - GAP

    try:
        with PILImage.open(img_path) as im:
            w_px, h_px = im.size
        aspect = h_px / w_px
    except Exception:
        aspect = 9 / 16

    img_w = slot_w
    img_h = img_w * aspect
    if img_h > max_img_h:
        img_h = max_img_h
        img_w = img_h / aspect

    # Centre image horizontally within slot
    img_x = x + (slot_w - img_w) / 2.0
    img_rect = fitz.Rect(img_x, y, img_x + img_w, y + img_h)

    # Light grey border around screenshot
    page.draw_rect(img_rect, color=(0.7, 0.7, 0.7), width=0.5)
    page.insert_image(img_rect, filename=img_path)

    # Caption (italic, centred)
    cap_y = y + img_h + GAP
    page.insert_textbox(
        fitz.Rect(x, cap_y, x + slot_w, cap_y + CAP_H),
        caption,
        fontname="heit",
        fontsize=8,
        align=fitz.TEXT_ALIGN_CENTER,
        color=(0.25, 0.25, 0.25),
    )

    return img_h + GAP + CAP_H


def build_ui_pages():
    """Return a fitz.Document containing the new UI pages."""
    tmp = fitz.open()

    # Group images: 2 per page
    pairs = [IMAGES[i:i+2] for i in range(0, len(IMAGES), 2)]

    for pg_idx, pair in enumerate(pairs):
        page = tmp.new_page(width=PAGE_W, height=PAGE_H)
        printed_num = INSERT_AFTER + 1 + pg_idx   # 33, 34, 35, 36, 37
        draw_header(page, printed_num)

        y = MARGIN_TOP_CONTENT

        # Section heading on first UI page only
        if pg_idx == 0:
            page.insert_text(
                (MARGIN_X, y + 13),
                "4.3  User Interface",
                fontname="hebo", fontsize=13, color=(0, 0, 0),
            )
            y += 22

            intro = (
                "The SmartBite web application (React, port 3000) provides a clean, "
                "responsive interface covering the complete ordering flow: landing page, "
                "restaurant discovery, menu browsing, cart management, payment, and account "
                "settings. The following figures show each screen in order."
            )
            page.insert_textbox(
                fitz.Rect(MARGIN_X, y, PAGE_W - MARGIN_X, y + 38),
                intro,
                fontname="helv", fontsize=10,
                align=fitz.TEXT_ALIGN_LEFT, color=(0, 0, 0),
            )
            y += 44

        # Divide remaining vertical space equally between the images
        avail_h = PAGE_H - MARGIN_BOT - y
        img_gap  = 14.0
        slot_h   = (avail_h - img_gap * (len(pair) - 1)) / len(pair)

        for k, (filename, caption) in enumerate(pair):
            img_path = os.path.join(ASSETS_DIR, filename)
            used = place_screenshot(page, img_path, caption,
                                    MARGIN_X, y, CONTENT_W, slot_h)
            y += used + img_gap

    return tmp


def main():
    print("Opening original PDF …")
    doc = fitz.open(PDF_PATH)
    original_count = doc.page_count
    print(f"  Original pages: {original_count}")

    print("Building UI pages …")
    ui_doc = build_ui_pages()
    print(f"  UI pages created: {ui_doc.page_count}")

    print(f"Inserting UI pages after page index {INSERT_AFTER} …")
    doc.insert_pdf(ui_doc, start_at=INSERT_AFTER + 1)

    ui_doc.close()

    print("Saving …")
    tmp_path = PDF_PATH + ".tmp"
    doc.save(tmp_path, garbage=4, deflate=True)
    doc.close()

    import shutil
    shutil.move(tmp_path, PDF_PATH)

    final = fitz.open(PDF_PATH)
    print(f"Done. Final page count: {final.page_count}")
    final.close()


if __name__ == "__main__":
    main()
