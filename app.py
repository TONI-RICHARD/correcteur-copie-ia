import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import pandas as pd
import io
import zipfile

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="IA Correcteur de Copies", layout="wide", page_icon="📝")

# Configuration de l'API (à remplir dans les secrets de Streamlit)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Clé API manquante. Configurez GOOGLE_API_KEY dans les secrets.")

model = genai.GenerativeModel('gemini-1.5-flash')

# --- FONCTIONS TECHNIQUES ---

def generer_pdf(nom_eleve, matiere, note, observation, correction):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Rapport de Correction : {matiere}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Élève : {nom_eleve}", ln=True)
    pdf.cell(0, 10, f"Note : {note}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "I", 11)
    pdf.multi_cell(0, 10, f"Observation : {observation}")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Détails de la correction :", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 8, correction.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S')

def analyser_copie(image, matiere, bareme):
    prompt = f"""
    Analyse cette copie d'élève pour la matière : {matiere}.
    Utilise ce barème : {bareme}.
    Réponds TOUJOURS au format suivant :
    [NOTE] : Note/20
    [OBSERVATION] : Résumé court
    [DETAILS] : Correction détaillée
    """
    response = model.generate_content([prompt, image])
    text = response.text
    
    # Extraction basique
    try:
        note = text.split("[NOTE] :")[1].split("\n")[0].strip()
        obs = text.split("[OBSERVATION] :")[1].split("\n")[0].strip()
        details = text.split("[DETAILS] :")[1].strip()
    except:
        note, obs, details = "N/A", "Erreur d'analyse", text
        
    return note, obs, details

# --- INTERFACE UTILISATEUR ---

st.title("🎓 Système de Correction Automatisé par IA")
st.markdown("---")

# Barre latérale de configuration
with st.sidebar:
    st.header("⚙️ Paramètres")
    matiere = st.text_input("Matière", "Français")
    bareme = st.text_area("Barème & Instructions", "Note sur 20. 5 points pour la forme, 15 points pour le fond.")
    password = st.text_input("Mot de passe d'accès", type="password")

# Vérification du mot de passe simple
if password != st.secrets.get("APP_PASSWORD", "admin123"):
    st.warning("Veuillez entrer le mot de passe dans la barre latérale pour débloquer l'outil.")
    st.stop()

# Zone de téléchargement
uploaded_files = st.file_uploader("Télécharger les scans des copies (Images)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"🚀 Corriger les {len(uploaded_files)} copies"):
        data_excel = []
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                img = Image.open(file)
                nom_eleve = file.name.split('.')[0]
                
                # Analyse IA
                note, obs, details = analyser_copie(img, matiere, bareme)
                
                # Génération PDF
                pdf_bytes = generer_pdf(nom_eleve, matiere, note, obs, details)
                zip_file.writestr(f"Correction_{nom_eleve}.pdf", pdf_bytes)
                
                # Ajout au tableau Excel
                data_excel.append({"Élève": nom_eleve, "Note": note, "Observation": obs})
                
                progress_bar.progress((i + 1) / len(uploaded_files))
        
        st.success("✅ Correction terminée !")
        
        # Boutons de téléchargement
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📦 Télécharger les PDFs (ZIP)", data=zip_buffer.getvalue(), file_name="corrections.zip")
        with col2:
            df = pd.DataFrame(data_excel)
            excel_io = io.BytesIO()
            df.to_excel(excel_io, index=False)
            st.download_button("📊 Télécharger le Tableau des Notes (Excel)", data=excel_io.getvalue(), file_name="notes.xlsx")
  
