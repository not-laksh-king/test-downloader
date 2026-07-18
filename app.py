import os, shutil, tempfile, warnings, subprocess, time
warnings.filterwarnings("ignore")
os.environ['MPLBACKEND'] = 'Agg'

import streamlit as st
from pdf2image import convert_from_path
from pix2text import Pix2Text

st.set_page_config(page_title="PDF → LaTeX Converter", layout="centered")
st.title("📚 Test Paper PDF → LaTeX + PDF Converter")
st.markdown("Upload your **test paper PDF**, get beautifully formatted LaTeX and PDF with all math rendered.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    if st.button("✨ Convert Now"):
        try:
            # Temporary directory
            tmpdir = tempfile.mkdtemp()
            pdf_path = os.path.join(tmpdir, "input.pdf")
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            progress_bar = st.progress(0, text="📄 Converting PDF to images...")
            images = convert_from_path(pdf_path, dpi=150)
            total = len(images)
            page_dir = os.path.join(tmpdir, "pages")
            os.makedirs(page_dir)
            for i, img in enumerate(images):
                img.save(os.path.join(page_dir, f"page_{i+1}.png"))

            progress_bar.progress(10, text="🧠 Loading AI models (first time may take a while)...")
            p2t = Pix2Text.from_config(device='cpu')
            md_parts = []

            for i in range(1, total+1):
                img_path = os.path.join(page_dir, f"page_{i}.png")
                out = p2t.recognize(img_path, file_type='page')
                md = out.to_markdown('page')
                md_parts.append(f"\n# Page {i}\n\n{md}\n\n\\newpage")
                progress = 10 + int(50 * (i / total))
                progress_bar.progress(progress, text=f"🔍 Recognizing page {i}/{total}")

            progress_bar.progress(60, text="🔄 Converting to LaTeX...")
            md_file = os.path.join(tmpdir, "temp.md")
            with open(md_file, "w", encoding="utf-8") as f:
                f.write("\n".join(md_parts))

            tex_file = os.path.join(tmpdir, "output.tex")
            subprocess.run([
                "pandoc", md_file,
                "-f", "markdown+tex_math_dollars",
                "-t", "latex",
                "-s", "-o", tex_file
            ], check=True)
            with open(tex_file, "r") as f:
                tex = f.read()
            tex = tex.replace(r"\begin{document}", r"\usepackage{amsmath, amssymb}\n\begin{document}")
            with open(tex_file, "w") as f:
                f.write(tex)

            progress_bar.progress(75, text="📄 Compiling PDF...")
            pdf_generated = False
            for attempt in range(2):
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "output.tex"],
                    cwd=tmpdir, capture_output=True, text=True
                )
                pdf_path_out = os.path.join(tmpdir, "output.pdf")
                if os.path.exists(pdf_path_out):
                    pdf_generated = True
                    break
                else:
                    if attempt == 0:
                        subprocess.run(["sudo", "tlmgr", "install", "collection-latexrecommended", "collection-latexextra"],
                                       capture_output=True)

            progress_bar.progress(100, text="✅ Done!")
            st.success("Conversion complete! Download your files below.")

            # Provide download buttons
            with open(tex_file, "rb") as f:
                st.download_button("📥 Download .tex file", f, file_name="output.tex", mime="application/x-tex")

            if pdf_generated:
                with open(pdf_path_out, "rb") as f:
                    st.download_button("📥 Download PDF", f, file_name="output.pdf", mime="application/pdf")
            else:
                st.warning("PDF compilation failed. You can use the .tex file on Overleaf to get the PDF.")

        except Exception as e:
            st.error(f"Conversion failed: {str(e)}")
