from io import BytesIO, StringIO
import streamlit as st
from PIL import Image
from Bio import Entrez, SeqIO
import requests

st.set_page_config(page_title="BIF Tool", layout="centered")

Entrez.email = "your.email@example.com"

st.title("From NCBI Accession Number To The Organism Image")
st.markdown("Enter an NCBI Accession Number (`NC_` for chromosomes or `NM_` for a specific gene).")

acc_number = st.text_input("Enter Accession Number:", "")

if st.button("Fetch and Analyze"):
    if not acc_number:
        st.warning("Please enter a valid Accession number.")
    else:
        with st.spinner(f"Fetching record for '{acc_number}' from NCBI..."):
            try:
                # 1. جلب بيانات GenBank للمعلومات والجينات
                fetch_handle = Entrez.efetch(db="nucleotide", id=acc_number, rettype="gb", retmode="text")
                gb_data = fetch_handle.read()
                fetch_handle.close()
                
                gb_io = StringIO(gb_data)
                record = SeqIO.read(gb_io, "genbank")
                
                # 2. جلب تسلسل FASTA مباشرة لتجنب خطأ Undefined Sequence
                fasta_handle = Entrez.efetch(db="nucleotide", id=acc_number, rettype="fasta", retmode="text")
                fasta_data = fasta_handle.read()
                fasta_handle.close()
                
                fasta_io = StringIO(fasta_data)
                fasta_record = SeqIO.read(fasta_io, "fasta")
                sequence_data = str(fasta_record.seq)

                scientific_name = record.annotations.get("organism", "Unknown Organism")
                description = record.description
                is_chromosome = acc_number.upper().startswith("NC")
                
                gene_name = "Not Available"
                gene_function = "Not Available"
                gene_location = "Not Available"
                
                for feature in record.features:
                    if feature.type == "CDS":
                        if "gene" in feature.qualifiers:
                            gene_name = feature.qualifiers["gene"][0]
                        if "product" in feature.qualifiers:
                            gene_function = feature.qualifiers["product"][0]
                        gene_location = f"{feature.location.start + 1} to {feature.location.end} bp"
                        break
                    elif feature.type == "gene" and gene_name == "Not Available":
                        if "gene" in feature.qualifiers:
                            gene_name = feature.qualifiers["gene"][0]
                        gene_location = f"{feature.location.start + 1} to {feature.location.end} bp"

                # iNaturalist API
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

                fasta_text = f">{record.id} {record.description}\n{sequence_data}"

                # Tabs
                tab1, tab2, tab3, tab4 = st.tabs([
                    "Organism Overview", 
                    "Gene Function Analysis", 
                    "FASTA Sequence", 
                    "Bioinformatics Tools"
                ])
                
                with tab1:
                    st.markdown("")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Accession:** `{acc_number}`")
                        st.write(f"**Scientific Name:** *{scientific_name}*")
                        st.write(f"**Common Name:** {common_name}")
                        st.metric(label="Sequence Length", value=f"{len(sequence_data):,} bp")
                    
                    with col2:
                        if image_url:
                            img_res = requests.get(image_url)
                            img = Image.open(BytesIO(img_res.content))
                            st.image(img, caption=scientific_name, use_container_width=True)
                        else:
                            st.warning("No image available for this organism.")
                
                with tab2:
                    st.subheader("Functional Annotation & Locus Details")
                    if is_chromosome:
                        st.info(f"**Record Description:** {description}")
                        st.warning(" **Note:** This is an **`NC_`** chromosome record containing a full genomic molecule with multiple loci, rather than an isolated single gene.")
                    else:
                        st.info(f"**Gene Name:** `{gene_name}`")
                        st.write(f"**Function:** {gene_function}")
                        st.success(f" **Internal Genomic Locus:** Located at position **{gene_location}**.")

                with tab3:
                    st.subheader("FASTA Sequence")
                    st.text_area("FASTA Format:", fasta_text, height=300)
                    st.download_button(
                        label="Download FASTA File",
                        data=fasta_text,
                        file_name=f"{acc_number}.fasta",
                        mime="text/plain"
                    )

                with tab4:
                    st.subheader("Bioinformatics Tools")
                    st.caption("External and analytical utilities designed to process the retrieved genomic sequence.")
                    
                    t_col1, t_col2, t_col3 = st.columns(3, gap="medium")

                    with t_col1:
                        with st.container(border=True):
                            st.subheader("NCBI ORF finder")
                            st.write("Identifies potential open reading frames.")
                            st.caption("Copy the FASTA sequence first")
                            st.link_button(
                                ":material/open_in_new: Open ORF finder",
                                "https://ncbi.leemina.moe/orffinder/"
                            )
                           
                    with t_col2:
                        with st.container(border=True):
                            st.subheader("Primer3")
                            st.write("Primer design tool.")
                            st.caption("Copy the FASTA sequence first")
                            st.link_button(
                                ":material/open_in_new: Open Primer3",
                                "https://primer3.ut.ee/"
                            )

                    with t_col3:
                        with st.container(border=True):
                            st.subheader("Expasy translate")
                            st.write("Translate nucleotide sequence.")
                            st.caption("Copy the FASTA sequence first")
                            st.link_button(
                                ":material/open_in_new: Open Expasy",
                                "https://web.expasy.org/translate/"
                            )
                        
            except Exception as e:
                st.error(f"An error occurred while processing the request: {e}")
