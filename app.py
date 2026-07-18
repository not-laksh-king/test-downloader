import os, shutil, tempfile, warnings, subprocess
import streamlit as st
from pdf2image import convert_from_path
from pix2text import Pix2Text

warnings.filterwarnings("ignore")
os.environ['MPLBACKEND'] = 'Agg'

st.set_page_config(page_title="PDF → LaTeX Converter")
st.title("📚 Test Paper PDF → LaTeX Converter")
st.markdown("Upload your question paper PDF, get **.tex file** and **compiled PDF** (if possible).")

uploaded_file = st.file_uploader("Choose a PDF", type="pdf")

if uploaded_file is not None:
    if st.button("✨ Convert Now"):
        try:
            tmpdir = tempfile.mkdtemp()
            pdf_path = os.path.join(tmpdir, "input.pdf")
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            # Step 1: PDF -> Images (200 DPI as original)
            progress = st.progress(0, text="📄 Converting PDF to images...")
            images = convert_from_path(pdf_path, dpi=200)
            total = len(images)
            page_dir = os.path.join(tmpdir, "pages")
            os.makedirs(page_dir)
            for i, img in enumerate(images):
                img.save(os.path.join(page_dir, f"page_{i+1}.png"), "PNG")

            # Step 2: Load Pix2Text
            progress.progress(10, text="🧠 Loading AI model...")
            p2t = Pix2Text.from_config()   # default device

            # Step 3: Build .tex directly (same as Colab)
            tex_lines = []
            tex_lines.append(r"\documentclass[12pt]{article}")
            tex_lines.append(r"\usepackage{amsmath, amssymb}")
            tex_lines.append(r"\begin{document}")

            for i in range(1, total+1):
                img_path = os.path.join(page_dir, f"page_{i}.png")
                out = p2t.recognize(img_path, file_type='page')
                page_md = out.to_markdown('page')          # markdown with $$ math
                tex_lines.append(f"\n% --- Page {i} ---\n")
                tex_lines.append(page_md)
                tex_lines.append(r"\newpage")
                percent = int(10 + 70 * (i / total))
                progress.progress(percent, text=f"🔍 Recognizing page {i}/{total}")

            tex_lines.append(r"\end{document}")
            tex_content = "\n".join(tex_lines)

            # Save .tex
            tex_path = os.path.join(tmpdir, "output.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(tex_content)

            progress.progress(90, text="📄 Compiling PDF (if LaTeX available)...")
            pdf_path_out = os.path.join(tmpdir, "output.pdf")
            pdf_generated = False

            # Attempt to compile with pdflatex (if installed)
            try:
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "output.tex"],
                    cwd=tmpdir, capture_output=True, text=True, timeout=120
                )
                if os.path.exists(pdf_path_out):
                    pdf_generated = True
            except:
                pass   # if pdflatex missing, ignore

            progress.progress(100, text="✅ Done!")
            st.success("Conversion complete!")

            # Download buttons
            with open(tex_path, "rb") as f:
                st.download_button("📥 Download .tex file", f, file_name="output.tex", mime="application/x-tex")

            if pdf_generated:
                with open(pdf_path_out, "rb") as f:
                    st.download_button("📥 Download PDF", f, file_name="output.pdf", mime="application/pdf")
            else:
                st.warning("PDF compilation failed (pdflatex not available). You can compile the .tex file on Overleaf for free!")

        except Exception as e:
            st.error(f"Conversion failed: {e}")
