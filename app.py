import mimetypes
mimetypes.init()
mimetypes.add_type(
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xlsx'
)

import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from tempfile import NamedTemporaryFile
from PIL import Image as PILImage
from io import BytesIO
import tempfile
import os

# ================= UI =================
st.markdown("## 🍰 Servando Recipe Card Generator")
st.caption("Costing • Standardization • Production")
st.caption("by Dong Cruz - Updated: 032026")
st.divider()

# ================= LOAD =================
cost_df = pd.read_excel("costs.xlsx")
cost_df.columns = cost_df.columns.str.strip()  # FIXED

ingredients = cost_df.iloc[:, 0].dropna().tolist()

if "items" not in st.session_state:
    st.session_state["items"] = []

# ================= DETAILS =================
st.markdown("### 📌 Recipe Details")

recipe_name = st.text_input("Recipe Name")
category = st.text_input("Category")

col1, col2, col3 = st.columns(3)

with col1:
    total_yield = st.number_input("Total Recipe Yield", min_value=0.0)

with col2:
    serving_size = st.number_input("Serving Size", min_value=0.0)

with col3:
    servings = total_yield / serving_size if serving_size > 0 else 0
    st.metric("No. of Servings", f"{servings:.0f}")

st.divider()

# ================= ADD INGREDIENT =================
st.markdown("### ➕ Add Ingredient")

col1, col2 = st.columns(2)

with col1:
    ingredient = st.selectbox("Ingredient", ingredients)

with col2:
    qty = st.number_input("Quantity", min_value=0.0)

if st.button("Add Ingredient"):
    try:
        row = cost_df[cost_df.iloc[:, 0] == ingredient].iloc[0]

        unit_cost = float(row.iloc[1])   # FIXED
        uom = str(row.iloc[2])          # FIXED
        packaging = 1000 if uom.lower() in ["g", "ml"] else 1

        st.session_state["items"].append({
            "ingredient": ingredient,
            "qty": qty,
            "packaging": packaging,
            "uom": uom,
            "unit_cost": unit_cost
        })
    except:
        st.error("Error adding ingredient. Check your costs.xlsx format.")

# ================= INGREDIENT LIST =================
st.markdown("### 📋 Ingredients List")

delete_index = None

for i, item in enumerate(st.session_state["items"]):
    with st.expander(item["ingredient"]):

        col1, col2 = st.columns(2)

        with col1:
            item["qty"] = st.number_input(f"Qty {i}", value=float(item["qty"]), key=f"qty_{i}")
            item["packaging"] = st.number_input(f"Packaging {i}", value=float(item["packaging"]), key=f"pack_{i}")

        with col2:
            item["uom"] = st.text_input(f"UOM {i}", value=item["uom"], key=f"uom_{i}")
            item["unit_cost"] = st.number_input(f"Unit Cost {i}", value=float(item["unit_cost"]), key=f"cost_{i}")

        if st.button(f"❌ Delete {item['ingredient']}", key=f"delete_{i}"):
            delete_index = i

if delete_index is not None:
    st.session_state["items"].pop(delete_index)
    st.rerun()

# ================= COST =================
total = 0

if st.session_state["items"]:
    df = pd.DataFrame(st.session_state["items"])
    df["total_cost"] = df["qty"] * df["unit_cost"]
    st.dataframe(df)

    total = df["total_cost"].sum()
    st.subheader(f"Total Recipe Cost: ₱{total:.2f}")

    st.markdown("### 💰 Pricing (SRP-Based)")

    col1, col2 = st.columns(2)

    with col1:
        srp = st.number_input("Selling Price (SRP)", min_value=0.0)

    with col2:
        if srp > 0:
            st.metric("Food Cost %", f"{(total/srp)*100:.2f}%")
            st.metric("Profit", f"₱{srp-total:,.2f}")

# ================= CLEAR =================
if st.button("Clear All"):
    st.session_state["items"] = []
    st.rerun()

# ================= PROCEDURE =================
st.markdown("### 🧑‍🍳 Procedure")
procedure = st.text_area("Write procedure (one step per line)")

# ================= SIGN =================
st.markdown("### ✍️ Sign-Off")

col1, col2 = st.columns(2)

with col1:
    prepared_by = st.text_input("Prepared By")

with col2:
    checked_by = st.text_input("Checked By")

# ================= IMAGES =================
images = st.file_uploader(
    "Upload Photos",
    type=["png","jpg","jpeg"],
    accept_multiple_files=True
)

# ================= GENERATE =================
if st.button("Generate Excel"):

    try:
        wb = load_workbook("template.xlsx")
        ws = wb.active

        ws["A3"] = recipe_name
        ws["A6"] = category
        ws["A55"] = recipe_name
        ws["A58"] = category

        ws["A8"] = total_yield
        ws["C8"] = serving_size
        ws["F8"] = servings

        ws["H47"] = prepared_by
        ws["H51"] = checked_by

        start_row = 13

        for i, item in enumerate(st.session_state["items"]):
            r = start_row + i
            ws[f"A{r}"] = item["ingredient"]
            ws[f"B{r}"] = item["qty"]
            ws[f"C{r}"] = item["packaging"]
            ws[f"D{r}"] = item["uom"]
            ws[f"F{r}"] = item["unit_cost"]

        for r in range(start_row + len(st.session_state["items"]), 41):
            for col in ["A","B","C","D","E","F","G","H"]:
                ws[f"{col}{r}"] = None

        row_cursor = 62
        for i, line in enumerate(procedure.split("\n"), start=1):
            if line.strip():
                ws[f"A{row_cursor}"] = f"Step {i}: {line}"
                row_cursor += 1

        START_ROW = 66
        COLS = ["A", "D", "G"]
        IMG_WIDTH = 240
        IMG_HEIGHT = 160

        row_pos = START_ROW
        col_index = 0
        temp_images = []

        for img_file in images or []:
            try:
                img_file.seek(0)

                pil_img = PILImage.open(img_file).convert("RGB")
                buffer = BytesIO()
                pil_img.save(buffer, format="PNG")
                buffer.seek(0)

                with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(buffer.read())
                    temp_img_path = tmp.name

                temp_images.append(temp_img_path)

                img = XLImage(temp_img_path)
                img.width = IMG_WIDTH
                img.height = IMG_HEIGHT

                ws.add_image(img, f"{COLS[col_index]}{row_pos}")

                col_index += 1
                if col_index == 3:
                    col_index = 0
                    row_pos += 16

            except:
                pass

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            temp_path = tmp.name

        wb.save(temp_path)

        for path in temp_images:
            try:
                os.remove(path)
            except:
                pass

        with open(temp_path, "rb") as f:
            file_data = f.read()

        os.remove(temp_path)

        file_name = f"{recipe_name.strip().replace(' ', '_')}.xlsx" if recipe_name else "recipe.xlsx"

        st.download_button(
            label="Download Excel",
            data=file_data,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Failed to generate Excel: {e}")