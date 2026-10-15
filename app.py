from io import BytesIO, StringIO
import streamlit as st
from PIL import Image
from Bio import Entrez
import requests
from Bio import SeqIO

st.set_page_config(page_title="NCBI Botanical Tool", layout="centered")
Entrez.email = "your.email@example.com"

st.title("From NCBI Accession to Organism Image")
st.markdown("Enter an NCBI Accession Number to fetch record details, scientific name, and organsim image.")

acc_number = st.text_input("Enter Accession Number:", "")

if st.button("Fetch and Analyze"):
    if not acc_number:
        st.warning("Please enter a valid Accession number.")
    else:
        with st.spinner(f"Fetching record for '{acc_number}' from NCBI..."):
            try:
                fetch_handle = Entrez.efetch(db="nucleotide", id=acc_number, rettype="fasta", retmode="text")
                fasta_data = fetch_handle.read()
                fetch_handle.close()
                
                fasta_io = StringIO(fasta_data)
                record = SeqIO.read(fasta_io, "fasta")
                description = record.description
                sequence_data = str(record.seq)
                
                parts = description.split()
                if len(parts) >= 3:
                    scientific_name = f"{parts[1]} {parts[2]}"
                elif len(parts) == 2:
                    scientific_name = parts[1]
                else:
                    scientific_name = "Unknown Organism"
                
                scientific_name = scientific_name.replace(",", "").replace("(", "").replace(")", "")
                
                inat_url = f"https://api.inaturalist.org/v1/taxa?q={scientific_name}&per_page=1"
                response = requests.get(inat_url).json()
                
                common_name = "Not Available"
                image_url = None
                results_list = response.get("results", [])
                
                if results_list:
                    taxon = results_list[0]
                    common_name = taxon.get("preferred_common_name", "Not Available")
                    if taxon.get("default_photo"):
                        image_url = taxon["default_photo"]["medium_url"]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Genomic Report")
                    st.write(f"**Accession:** {acc_number}")
                    st.write(f"**Scientific Name:** *{scientific_name}*")
                    st.write(f"**Common Name:** {common_name}")
                    st.metric(label="Sequence Length", value=f"{len(sequence_data):,} bp")
                
                with col2:
                    st.subheader("Organism Image")
                    if image_url:
                        img_res = requests.get(image_url)
                        img = Image.open(BytesIO(img_res.content))
                        st.image(img, caption=scientific_name, use_container_width=True)
                    else:
                        st.warning("No image available for this organism.")
                        
            except Exception as e:
                st.error(f"An error occurred while processing the request: {e}")