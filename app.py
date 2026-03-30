import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

# Configurazione della pagina
st.set_page_config(page_title="Diario Calisthenics", page_icon="💪", layout="wide")

# --- MAGIA DEL CLOUD: CONNESSIONE A GOOGLE SHEETS ---
NOME_FOGLIO_GOOGLE = "Allenamenti_Calisthenics"

@st.cache_resource(ttl=60)
def init_connection():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_data():
    client = init_connection()
    sheet = client.open(NOME_FOGLIO_GOOGLE).sheet1
    dati = sheet.get_all_records()
    df = pd.DataFrame(dati)
    if df.empty:
        colonne = ['Data', 'PT', 'Lezioni_Rimaste', 'Metodo', 'Esercizio', 'Attrezzo', 'Serie', 'Rep_Target', 'Carico_kg', 'Tipo_Var', 'Sec_Var', 'Tipo_Var_2', 'Sec_Var_2', 'Rest_sec', 'Tempo_Esec_sec', 'Resoconto_Auto', 'Note_Esecuzione']
        return pd.DataFrame(columns=colonne)
    return df

def append_data(df_nuovo):
    client = init_connection()
    sheet = client.open(NOME_FOGLIO_GOOGLE).sheet1
    df_nuovo = df_nuovo.fillna("") 
    sheet.append_rows(df_nuovo.values.tolist())

# --- INIZIALIZZAZIONE DELLA MEMORIA ---
if 'carrello' not in st.session_state:
    st.session_state.carrello = []
if 'salvato_con_successo' not in st.session_state:
    st.session_state.salvato_con_successo = False
if 'diario_periodo' not in st.session_state:
    st.session_state.diario_periodo = "1M"
if 'diario_offset' not in st.session_state:
    st.session_state.diario_offset = 0

st.title("💪 Diario Calisthenics 💪") 

# --- CREAZIONE DELLE SCHEDE (TABS) ---
tab_inserimento, tab_diario, tab_analisi = st.tabs(["✏️ Inserimento Dati", "📖 Diario Allenamenti", "📈 Analisi Progressi"])

# ==========================================
# SCHEDA 1: INSERIMENTO DATI
# ==========================================
with tab_inserimento:
    if st.session_state.salvato_con_successo:
        st.success("✅ Allenamento salvato in Cloud con successo!")
        st.session_state.salvato_con_successo = False 

    carrello_pieno = len(st.session_state.carrello) > 0
    lezioni_rimaste = 0
    ultima_data_pt = None
    data_corrente_selezionata = st.session_state.get('data_input', datetime.today().date())

    try:
        df_esistente = get_data()
        if 'Lezioni_Rimaste' not in df_esistente.columns:
            df_esistente['Lezioni_Rimaste'] = 0
            
        df_pt = df_esistente[df_esistente['PT'] == 'Sì']
        if not df_pt.empty:
            ultima_riga_pt = df_pt.iloc[-1]
            lezioni_rimaste_precedenti = int(ultima_riga_pt['Lezioni_Rimaste'])
            ultima_data_pt = str(ultima_riga_pt['Data'])
            data_corrente_str = data_corrente_selezionata.strftime("%d/%m/%Y")
            
            if data_corrente_str == ultima_data_pt:
                lezioni_rimaste = lezioni_rimaste_precedenti
            else:
                lezioni_rimaste = lezioni_rimaste_precedenti - 1
    except Exception:
        lezioni_rimaste = 0

    st.subheader("Compila l'esercizio")

    col1, col2 = st.columns(2)
    with col1:
        data_all = st.date_input("Data", key="data_input", disabled=carrello_pieno)
    with col2:
        pt = st.selectbox("Con PT?", ["Sì", "No"], disabled=carrello_pieno)

    lezioni_da_salvare = 0

    if pt == "Sì":
        st.markdown("---")
        if lezioni_rimaste > 0:
            opzioni = [f"In corso ({lezioni_rimaste} rimaste)", "10", "20", "NotDefined"]
            scelta_pacchetto = st.selectbox("📦 Stato Pacchetto PT", opzioni, disabled=carrello_pieno)
            if scelta_pacchetto.startswith("In corso"):
                lezioni_da_salvare = lezioni_rimaste
            elif scelta_pacchetto in ["10", "20"]:
                lezioni_da_salvare = int(scelta_pacchetto)
            else:
                lezioni_da_salvare = 0
        else:
            opzioni = ["NotDefined", "10", "20"]
            scelta_pacchetto = st.selectbox("📦 Nuovo Pacchetto (⚠️ LEZIONI ESAURITE)", opzioni, disabled=carrello_pieno)
            if scelta_pacchetto in ["10", "20"]:
                lezioni_da_salvare = int(scelta_pacchetto)
            else:
                lezioni_da_salvare = 0
        st.markdown("---")
    else:
        lezioni_da_salvare = 0

    st.markdown("**Esercizio e Tipologia**") 
    col3, col4, col5 = st.columns(3)
    with col3:
        metodo = st.selectbox("Metodo", ["Normale", "EMOM", "Double EMOM", "AMRAP", "RT", "Circuito", "Drop Set", "Complex"])
    with col4:
        esercizio = st.text_input("Esercizio (es. Chin up, Dip, Bulgarian)")
    with col5:
        attrezzo = st.selectbox("Attrezzo", ["Corpo Libero", "Zavorra", "Manubrio Singolo", "Manubrio Doppio", "Bilanciere", "Multipower", "Macchinario"])

    emom_min, emom_rep, emom_ogni, emom_rep_1, emom_rep_2 = 0, 0, 0.0, 0, 0
    rep_non_costanti = False
    rep_amrap_list = []
    carico = 0.0

    st.markdown("**Set e Carichi**")

    if metodo in ["EMOM", "Double EMOM"]:
        rep_non_costanti = st.checkbox("🔄 Rep non costanti (es. alternate pari/dispari)")
        if rep_non_costanti:
            col_emom1, col_rep1, col_rep2, col_emom3, col_carico = st.columns(5)
            with col_emom1: emom_min = st.number_input("Min. Tot.", min_value=1, value=10, step=1)
            with col_rep1: emom_rep_1 = st.number_input("Rep 1", min_value=0, value=2, step=1)
            with col_rep2: emom_rep_2 = st.number_input("Rep 2", min_value=0, value=3, step=1)
            with col_emom3: emom_ogni = st.number_input("Ogni (m)", min_value=0.5, value=1.0, step=0.5)
            with col_carico: carico = st.number_input("Carico", min_value=0.0, value=0.0, step=0.5) if attrezzo != "Corpo Libero" else 0.0
            rep_da_salvare = emom_rep_1 
            serie_da_salvare = int(emom_min / emom_ogni)
        else:
            col_emom1, col_emom2, col_emom3, col_carico = st.columns(4)
            with col_emom1: emom_min = st.number_input("Min. Tot.", min_value=1, value=10, step=1)
            with col_emom2: emom_rep = st.number_input("Reps", min_value=1, value=5, step=1)
            with col_emom3: emom_ogni = st.number_input("Ogni (m)", min_value=0.5, value=1.0, step=0.5)
            with col_carico: carico = st.number_input("Carico", min_value=0.0, value=0.0, step=0.5) if attrezzo != "Corpo Libero" else 0.0
            rep_da_salvare = emom_rep
            serie_da_salvare = int(emom_min / emom_ogni)

    elif metodo == "AMRAP":
        col_serie, col_carico = st.columns(2)
        with col_serie: serie_da_salvare = st.number_input("Quante Serie AMRAP?", min_value=1, value=2, step=1)
        with col_carico: carico = st.number_input("Carico (kg)", min_value=0.0, value=0.0, step=0.5) if attrezzo != "Corpo Libero" else 0.0
        
        conta_reps = st.checkbox("🔢 Conta le ripetizioni (disattiva se vai a cedimento senza contare)", value=True)
        
        if conta_reps:
            st.markdown("**Inserisci le ripetizioni raggiunte per ogni serie:**")
            cols_amrap = st.columns(serie_da_salvare)
            for i in range(serie_da_salvare):
                with cols_amrap[i]:
                    rep_raggiunta = st.number_input(f"S. {i+1}", min_value=0, value=0, step=1, key=f"amrap_{i}")
                    rep_amrap_list.append(str(rep_raggiunta))
            rep_da_salvare = sum(int(r) for r in rep_amrap_list)
        else:
            rep_da_salvare = "" # Valore vuoto (diverso da zero!) per non distruggere le statistiche

    else:
        col6, col7, col8 = st.columns(3)
        with col6: serie_da_salvare = st.number_input("Serie", min_value=1, value=1, step=1)
        with col7: rep_da_salvare = st.number_input("Rep Target", min_value=0, value=5, step=1)
        with col8: carico = st.number_input("Carico (kg)", min_value=0.0, value=0.0, step=0.5) if attrezzo != "Corpo Libero" else 0.0

    st.markdown("---")
    mostra_varianti = st.checkbox("⚙️ Aggiungi Varianti Tecniche")
    tipo_var, tipo_var_2 = "", ""
    sec_var, sec_var_2, rest, tempo_esec = 0, 0, 0, 0

    if mostra_varianti:
        st.markdown("**Varianti**")
        col_var_testo, col_var_num = st.columns(2)
        with col_var_testo:
            tipo_var = st.text_input("Tipo Variante 1 (es. Isometria 90°)")
            tipo_var_2 = st.text_input("Tipo Variante 2 (es. Eccentrica)")
        with col_var_num:
            if tipo_var != "": sec_var = st.number_input("Sec. Variante 1", min_value=0, value=0, step=1)
            if tipo_var_2 != "": sec_var_2 = st.number_input("Sec. Variante 2", min_value=0, value=0, step=1)
                
    if metodo not in ["EMOM", "Double EMOM", "Circuito", "RT"]:
        st.markdown("---")    
        st.markdown("**Recupero**")
        rest = st.number_input("Recupero (sec)", min_value=0, value=0, step=10)
                
    if metodo in ["Circuito", "RT"]:
        st.markdown("---")    
        st.markdown("**Tempo**") 
        tempo_esec = st.number_input("Tempo Esec. (sec)", min_value=0, value=0, step=1)

    st.markdown("---")
    st.markdown("**Note (opzionali)**")
    note = st.text_area("Aggiungi note personali (es. cedimento precoce, dolore spalla)")

    if st.button("➕ Aggiungi al Riepilogo"):
        if esercizio == "":
            st.error("⚠️ Inserisci il nome dell'esercizio prima di aggiungere!")
        else:
            str_carico = f"{int(carico)}" if carico % 1 == 0 else f"{carico}"
            
            if metodo in ["EMOM", "Double EMOM"]:
                if emom_ogni % 1 == 0: str_ogni = f"{int(emom_ogni)}'"
                else:
                    m_ogni = int(emom_ogni)
                    s_ogni = int((emom_ogni - m_ogni) * 60)
                    str_ogni = f"{s_ogni}''" if m_ogni == 0 else f"{m_ogni}' {s_ogni}''"

                prefisso_emom = f"{metodo} {int(emom_min)}' {esercizio}"
                if carico > 0: prefisso_emom += f" + {str_carico}kg"
                    
                if rep_non_costanti: prefisso = f"{prefisso_emom} alternate {int(emom_rep_1)}/{int(emom_rep_2)} rep ogni {str_ogni}"
                else: prefisso = f"{prefisso_emom} {int(emom_rep)} rep ogni {str_ogni}"
                    
            elif metodo == "AMRAP":
                if rep_da_salvare == "":
                    prefisso = f"AMRAP {esercizio} {int(serie_da_salvare)} Serie (A sfinimento)"
                else:
                    prefisso = f"AMRAP {esercizio} {int(serie_da_salvare)} Serie ({'-'.join(rep_amrap_list)})"
            else:
                if metodo == "Normale": prefisso = f"{esercizio} {int(serie_da_salvare)} X {int(rep_da_salvare)}"
                else: prefisso = f"{metodo} {esercizio} {int(serie_da_salvare)} X {int(rep_da_salvare)}"
                
            dettagli = []
            if metodo not in ["EMOM", "Double EMOM"] and carico > 0: dettagli.append(f"+ {str_carico}kg")
            if tipo_var != "": dettagli.append(f"{tipo_var} {sec_var}''" if sec_var > 0 else f"{tipo_var}")
            if tipo_var_2 != "": dettagli.append(f"{tipo_var_2} {sec_var_2}''" if sec_var_2 > 0 else f"{tipo_var_2}")
                    
            if rest > 0:
                if rest <= 90: str_rest = f"{int(rest)}''"
                else:
                    m = int(rest // 60)
                    s = int(rest % 60)
                    str_rest = f"{m}'" if s == 0 else f"{m}' {s}''"
                dettagli.append(f"{str_rest} rest")
                
            if tempo_esec > 0:
                if tempo_esec <= 90: str_tempo = f"{int(tempo_esec)}''"
                else:
                    m = int(tempo_esec // 60)
                    s = int(tempo_esec % 60)
                    str_tempo = f"{m}'" if s == 0 else f"{m}' {s}''"
                dettagli.append(f"in {str_tempo}")
                
            str_dettagli = " ".join(dettagli)
            resoconto_auto = f"[{prefisso} {str_dettagli}]" if str_dettagli else f"[{prefisso}]"

            nuovo_dato_dict = {
                'Data': data_all.strftime("%d/%m/%Y"), 
                'PT': pt,
                'Lezioni_Rimaste': lezioni_da_salvare, 
                'Metodo': metodo,
                'Esercizio': esercizio,
                'Attrezzo': attrezzo,
                'Serie': serie_da_salvare,
                'Rep_Target': rep_da_salvare,
                'Carico_kg': carico,
                'Tipo_Var': tipo_var,
                'Sec_Var': sec_var,
                'Tipo_Var_2': tipo_var_2,  
                'Sec_Var_2': sec_var_2,    
                'Rest_sec': rest,
                'Tempo_Esec_sec': tempo_esec,
                'Resoconto_Auto': resoconto_auto, 
                'Note_Esecuzione': note
            }
            
            st.session_state.carrello.append(nuovo_dato_dict)
            st.rerun()

    if len(st.session_state.carrello) > 0:
        st.markdown("---")
        data_allenamento = st.session_state.carrello[0]['Data']
        st.markdown(f"### 📋 Riepilogo Allenamento del {data_allenamento}")
        
        for i, item in enumerate(st.session_state.carrello):
            col_testo, col_up, col_down, col_elimina = st.columns([7, 1, 1, 1])
            with col_testo: st.markdown(f"🔸 **{item['Esercizio']}**: {item['Resoconto_Auto']}")
            with col_up:
                if i > 0:
                    if st.button("⬆️", key=f"up_{i}"):
                        st.session_state.carrello[i], st.session_state.carrello[i-1] = st.session_state.carrello[i-1], st.session_state.carrello[i]
                        st.rerun()
            with col_down:
                if i < len(st.session_state.carrello) - 1:
                    if st.button("⬇️", key=f"down_{i}"):
                        st.session_state.carrello[i], st.session_state.carrello[i+1] = st.session_state.carrello[i+1], st.session_state.carrello[i]
                        st.rerun()
            with col_elimina:
                if st.button("❌", key=f"elimina_{i}"):
                    st.session_state.carrello.pop(i)
                    st.rerun()
        
        if len(st.session_state.carrello) > 0:
            st.warning("⚠️ L'allenamento è pronto. Controlla il riepilogo e invia al Cloud!")
            col_salva, col_svuota = st.columns(2)
            with col_salva:
                if st.button("☁️ Salva su Google Sheets", type="primary"):
                    try:
                        df_anteprima = pd.DataFrame(st.session_state.carrello)
                        append_data(df_anteprima) # SCRIVE ONLINE!
                        st.session_state.carrello = []
                        st.session_state.salvato_con_successo = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Ops! Errore di connessione a Google Sheets: {e}")
            with col_svuota:
                if st.button("🗑️ Svuota tutto il Carrello"):
                    st.session_state.carrello = []
                    st.rerun()

# ==========================================
# SCHEDA 2: DIARIO ALLENAMENTI
# ==========================================
with tab_diario:
    try:
        df_diario = get_data()
        if df_diario.empty:
            st.info("Nessun allenamento trovato. Inizia ad inserire i dati!")
        else:
            df_diario['ID_Riga'] = df_diario.index
            
            df_diario['Carico_kg'] = pd.to_numeric(df_diario['Carico_kg'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            # ATTENZIONE: Niente ".fillna(0)" qui! Se il campo è vuoto, rimarrà un NaN innocuo e saggio.
            df_diario['Rep_Target'] = pd.to_numeric(df_diario['Rep_Target'].astype(str).str.replace(',', '.'), errors='coerce')
            df_diario['Data_Ord'] = pd.to_datetime(df_diario['Data'], format='%d/%m/%Y')
            
            st.markdown("### 📚 Il tuo Storico Allenamenti")
            
            periodo = st.radio("Seleziona il periodo visibile:", ["1M", "3M", "6M", "1A", "Tutto"], horizontal=True, label_visibility="collapsed")
            
            if st.session_state.diario_periodo != periodo:
                st.session_state.diario_periodo = periodo
                st.session_state.diario_offset = 0
                st.rerun()
                
            offset = st.session_state.diario_offset
            oggi_pd = pd.to_datetime(datetime.today().date())
            mesi_it = {1:"Gennaio", 2:"Febbraio", 3:"Marzo", 4:"Aprile", 5:"Maggio", 6:"Giugno", 7:"Luglio", 8:"Agosto", 9:"Settembre", 10:"Ottobre", 11:"Novembre", 12:"Dicembre"}

            if periodo == "1M":
                start_d = (oggi_pd + pd.DateOffset(months=offset)).replace(day=1)
                end_d = start_d + pd.DateOffset(months=1) - pd.Timedelta(days=1)
                if offset == 0: end_d = oggi_pd 
                label_periodo = f"{mesi_it[start_d.month]} {start_d.year}"
            elif periodo == "3M":
                start_d = (oggi_pd.replace(day=1) - pd.DateOffset(months=2)) + pd.DateOffset(months=offset*3)
                end_d = start_d + pd.DateOffset(months=3) - pd.Timedelta(days=1)
                if offset == 0: end_d = oggi_pd
                label_periodo = f"{mesi_it[start_d.month]} {start_d.year} - {mesi_it[end_d.month]} {end_d.year}"
            elif periodo == "6M":
                start_d = (oggi_pd.replace(day=1) - pd.DateOffset(months=5)) + pd.DateOffset(months=offset*6)
                end_d = start_d + pd.DateOffset(months=6) - pd.Timedelta(days=1)
                if offset == 0: end_d = oggi_pd
                label_periodo = f"{mesi_it[start_d.month]} {start_d.year} - {mesi_it[end_d.month]} {end_d.year}"
            elif periodo == "1A":
                start_d = oggi_pd.replace(month=1, day=1) + pd.DateOffset(years=offset)
                end_d = start_d.replace(month=12, day=31)
                if offset == 0: end_d = oggi_pd
                label_periodo = f"Anno {start_d.year}"
            else: 
                start_d = pd.to_datetime("2000-01-01")
                end_d = oggi_pd
                label_periodo = "Tutto lo storico"

            mask = (df_diario['Data_Ord'].dt.date >= start_d.date()) & (df_diario['Data_Ord'].dt.date <= end_d.date())
            df_periodo = df_diario.loc[mask].copy()

            st.markdown("<br>", unsafe_allow_html=True)
            if periodo != "Tutto":
                col_prev, col_label, col_next = st.columns([1, 6, 1])
                with col_prev:
                    if st.button("◀ Precedente", use_container_width=True):
                        st.session_state.diario_offset -= 1
                        st.rerun()
                with col_label:
                    st.markdown(f"<h4 style='text-align: center; margin-top: 0px;'>{label_periodo}</h4>", unsafe_allow_html=True)
                with col_next:
                    disabilita_avanti = (offset >= 0) 
                    if st.button("Successivo ▶", disabled=disabilita_avanti, use_container_width=True):
                        st.session_state.diario_offset += 1
                        st.rerun()
            else:
                st.markdown(f"<h4 style='text-align: center;'>{label_periodo}</h4>", unsafe_allow_html=True)

            if df_periodo.empty:
                st.info("Riposo totale in questo periodo! Nessun allenamento registrato.")
            else:
                if periodo == "Tutto":
                    df_periodo['Anno'] = df_periodo['Data_Ord'].dt.year.astype(str)
                    chart_data = df_periodo.groupby('Anno').size().reset_index(name='N_Esercizi')
                    x_axis = alt.X('Anno:N', title='', axis=alt.Axis(labelAngle=0))
                    tooltip_x = alt.Tooltip('Anno:N', title='Anno')
                else:
                    chart_data = df_periodo.groupby('Data_Ord').size().reset_index(name='N_Esercizi')
                    chart_data['Giorno'] = chart_data['Data_Ord'].dt.strftime('%d/%m')
                    x_axis = alt.X('Giorno:N', sort=alt.EncodingSortField(field='Data_Ord', order='ascending'), title='', axis=alt.Axis(labelAngle=-45))
                    tooltip_x = alt.Tooltip('Data_Ord:T', title='Data', format='%d/%m/%Y')

                chart_attivita = alt.Chart(chart_data).mark_bar(color='#ff4b4b', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                    x=x_axis,
                    y=alt.Y('N_Esercizi:Q', title='Esercizi Eseguiti', axis=alt.Axis(grid=True)),
                    tooltip=[tooltip_x, alt.Tooltip('N_Esercizi:Q', title='Esercizi')]
                ).properties(height=250)
                st.altair_chart(chart_attivita, use_container_width=True)

                st.markdown("##### 🏆 Highlights del Periodo")
                col_c1, col_c2, col_c3 = st.columns(3)
                
                top_ex = df_periodo['Esercizio'].value_counts().idxmax()
                top_ex_count = df_periodo['Esercizio'].value_counts().max()
                col_c1.metric("🥇 Esercizio più svolto", f"{top_ex}", f"{top_ex_count} sessioni")

                df_zavorre = df_periodo[df_periodo['Carico_kg'] > 0]
                if not df_zavorre.empty:
                    max_kg_idx = df_zavorre['Carico_kg'].idxmax()
                    max_kg = df_zavorre.loc[max_kg_idx, 'Carico_kg']
                    max_kg_ex = df_zavorre.loc[max_kg_idx, 'Esercizio']
                    str_kg = f"{max_kg:g}" 
                    col_c2.metric("⚖️ Picco di Forza", f"+{str_kg} kg", f"Esercizio: {max_kg_ex}")
                else:
                    col_c2.metric("⚖️ Picco di Forza", "Corpo Libero", "Nessuna zavorra")

                # Sicurezza: Eliminiamo eventuali righe "NaN" per trovare il vero record numerico
                df_zavorre_reps = df_zavorre.dropna(subset=['Rep_Target'])
                if not df_zavorre_reps.empty:
                    max_rep_idx = df_zavorre_reps['Rep_Target'].idxmax()
                    max_rep = int(df_zavorre_reps.loc[max_rep_idx, 'Rep_Target'])
                    max_rep_ex = df_zavorre_reps.loc[max_rep_idx, 'Esercizio']
                    max_rep_load = df_zavorre_reps.loc[max_rep_idx, 'Carico_kg']
                    str_rl = f"{max_rep_load:g}"
                    col_c3.metric("🔥 Resistenza Ponderata", f"{max_rep} reps", f"su {max_rep_ex} (+{str_rl}kg)")
                else:
                    col_c3.metric("🔥 Resistenza Ponderata", "-", "Nessuna rep registrata")

                st.markdown("---")
                st.markdown("##### 📝 Dettaglio Sessioni")
                
                df_periodo = df_periodo.sort_values(by=['Data_Ord', 'ID_Riga'], ascending=[False, True])
                giorni_allenamento_periodo = df_periodo['Data'].drop_duplicates().tolist()
                
                for giorno in giorni_allenamento_periodo:
                    esercizi_del_giorno = df_periodo[df_periodo['Data'] == giorno]
                    pt_svolto = esercizi_del_giorno.iloc[0]['PT']
                    lezioni_rimaste_giorno = esercizi_del_giorno.iloc[0].get('Lezioni_Rimaste', 0)
                    num_esercizi = len(esercizi_del_giorno)
                    
                    titolo_expander = f"🗓️ {giorno} | 🏋️‍♂️ {num_esercizi} Esercizi"
                    if pt_svolto == 'Sì': titolo_expander += f" | 👤 PT (Rimaste: {int(lezioni_rimaste_giorno)})"
                    
                    with st.expander(titolo_expander):
                        for index, riga in esercizi_del_giorno.iterrows():
                            testo_riga = f"🔸 <b>{riga['Esercizio']}</b>: {riga['Resoconto_Auto']}"
                            if pd.notna(riga['Note_Esecuzione']):
                                note_esec = str(riga['Note_Esecuzione']).strip()
                                if note_esec != "" and note_esec.lower() != "nan":
                                    testo_riga += f" - 📝 <i>{note_esec}</i>"
                                    
                            st.markdown(
                                f'<div style="padding-left: 1.6em; text-indent: -1.6em; margin-bottom: 0.5em;">{testo_riga}</div>', 
                                unsafe_allow_html=True
                            )
                            
    except Exception as e:
        st.error(f"⚠️ Errore di connessione a Google Sheets: {e}")

# ==========================================
# SCHEDA 3: ANALISI PROGRESSI
# ==========================================
with tab_analisi:
    st.subheader("📈 Analisi Progressi")
    
    try:
        df_analisi = get_data()
        if df_analisi.empty:
            st.info("Inizia a registrare allenamenti per sbloccare l'analisi dei dati!")
        else:
            df_analisi['ID_Riga'] = df_analisi.index
            
            df_analisi['Carico_kg'] = pd.to_numeric(df_analisi['Carico_kg'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_analisi['Serie'] = pd.to_numeric(df_analisi['Serie'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_analisi['Rest_sec'] = pd.to_numeric(df_analisi['Rest_sec'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            # Qui non forziamo lo zero (per la regola ASMAP/cedimento invisibile)
            df_analisi['Rep_Target'] = pd.to_numeric(df_analisi['Rep_Target'].astype(str).str.replace(',', '.'), errors='coerce')

            # Calcolo Volume Totale Sicuro e pulito
            df_analisi['Volume_Totale'] = df_analisi.apply(
                lambda row: row['Rep_Target'] if row['Metodo'] == 'AMRAP' else (row['Serie'] * row['Rep_Target']), 
                axis=1
            )

            df_analisi['Data_Ord'] = pd.to_datetime(df_analisi['Data'], format='%d/%m/%Y')
            df_analisi = df_analisi.sort_values(by=['Data_Ord', 'ID_Riga'], ascending=[True, True])

            min_date = df_analisi['Data_Ord'].min().date()
            max_date = df_analisi['Data_Ord'].max().date()

            st.markdown("##### 📅 Seleziona Periodo Globale")
            seleziona_date = st.date_input("", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            
            if isinstance(seleziona_date, tuple):
                if len(seleziona_date) == 2:
                    start_d, end_d = seleziona_date
                else:
                    start_d = end_d = seleziona_date[0]
            else:
                start_d = end_d = seleziona_date

            mask = (df_analisi['Data_Ord'].dt.date >= start_d) & (df_analisi['Data_Ord'].dt.date <= end_d)
            df_filtrato_date = df_analisi.loc[mask].copy()

            st.markdown("---")
            st.markdown(f"### 🌍 Panoramica Allenamenti (dal {start_d.strftime('%d/%m/%Y')} al {end_d.strftime('%d/%m/%Y')})")
            
            col_pie, col_bar = st.columns(2)
            with col_pie:
                st.markdown("**Distribuzione Attrezzi** *(Corpo Libero vs Zavorre)*")
                pie_chart = alt.Chart(df_filtrato_date).mark_arc(innerRadius=40).encode(
                    theta=alt.Theta(field="Attrezzo", type="nominal", aggregate="count"),
                    color=alt.Color(field="Attrezzo", type="nominal", legend=alt.Legend(title="Attrezzo")),
                    tooltip=['Attrezzo', alt.Tooltip('count()', title='Serie Registrate')]
                ).properties(height=300)
                st.altair_chart(pie_chart, use_container_width=True)
                
            with col_bar:
                st.markdown("**Top 10 Esercizi per Volume (Ripetizioni Totali)**")
                # Pandas somma tranquillamente saltando i NaN, quindi l'ASMAP non rompe niente!
                volume_esercizi = df_filtrato_date.groupby('Esercizio')['Volume_Totale'].sum().reset_index()
                top_esercizi = volume_esercizi.sort_values(by='Volume_Totale', ascending=False).head(10)
                
                bar_chart = alt.Chart(top_esercizi).mark_bar(color="#ff4b4b").encode(
                    y=alt.Y('Esercizio:N', sort='-x', title='', axis=alt.Axis(labelLimit=200)),
                    x=alt.X('Volume_Totale:Q', title='Ripetizioni Totali', axis=alt.Axis(grid=True)),
                    tooltip=[alt.Tooltip('Esercizio:N', title='Esercizio'), alt.Tooltip('Volume_Totale:Q', title='Reps Totali')]
                ).properties(height=300)
                st.altair_chart(bar_chart, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 🏆 I Tuoi Record Assoluti (Carico Massimo)")
            
            df_prs = df_filtrato_date[df_filtrato_date['Carico_kg'] > 0]
            
            if not df_prs.empty:
                lista_esercizi_pr = sorted(df_prs['Esercizio'].unique().tolist())
                esercizi_base = ["dip", "chin up", "pull up"]
                default_pr = [e for e in lista_esercizi_pr if e.lower().strip() in esercizi_base]
                
                esercizi_scelti_pr = st.multiselect(
                    "➕ Seleziona gli esercizi da mostrare:",
                    options=lista_esercizi_pr,
                    default=default_pr
                )
                
                if esercizi_scelti_pr:
                    df_prs_filtrato = df_prs[df_prs['Esercizio'].isin(esercizi_scelti_pr)]
                    pr_data = df_prs_filtrato.groupby('Esercizio')['Carico_kg'].max().reset_index()
                    
                    altezza_grafico = max(150, len(pr_data) * 50) 
                    
                    chart_pr = alt.Chart(pr_data).mark_bar(color='#ffaa00', cornerRadiusEnd=4).encode(
                        x=alt.X('Carico_kg:Q', title='Massimale Raggiunto (kg)', axis=alt.Axis(grid=True)),
                        y=alt.Y('Esercizio:N', sort='-x', title='', axis=alt.Axis(labelLimit=200)),
                        tooltip=[alt.Tooltip('Esercizio:N', title='Esercizio'), alt.Tooltip('Carico_kg:Q', title='Max (kg)')]
                    ).properties(height=altezza_grafico)
                    st.altair_chart(chart_pr, use_container_width=True)
                else:
                    st.info("Aggiungi almeno un esercizio dalla tendina qui sopra per vedere il grafico dei record.")
            else:
                st.info("Nessun carico aggiuntivo registrato in questo periodo (Hai lavorato solo a Corpo Libero puro).")

            st.markdown("---")
            
            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            with col_d1:
                lista_esercizi = df_filtrato_date['Esercizio'].dropna().unique().tolist()
                esercizio_selezionato = st.selectbox("🎯 Seleziona l'Esercizio:", [""] + lista_esercizi)

            if esercizio_selezionato:
                df_es = df_filtrato_date[df_filtrato_date['Esercizio'] == esercizio_selezionato].copy()
                
                with col_d2:
                    lista_metodi = df_es['Metodo'].dropna().unique().tolist()
                    metodo_selezionato = st.selectbox("⚙️ Filtra per Metodo:", ["Tutti"] + lista_metodi)

                with col_d3:
                    lista_attrezzi = df_es['Attrezzo'].dropna().unique().tolist()
                    attrezzo_selezionato = st.selectbox("🏋️‍♂️ Filtra per Attrezzo:", ["Tutti"] + lista_attrezzi)

                with col_d4:
                    lista_carichi = sorted(df_es['Carico_kg'].dropna().unique().tolist())
                    opzioni_carichi = ["Tutti"]
                    for c in lista_carichi:
                        if c == 0:
                            opzioni_carichi.append("Corpo Libero (0 kg)")
                        else:
                            str_c = f"{c:g}" 
                            opzioni_carichi.append(f"{str_c} kg")
                            
                    carico_selezionato = st.selectbox("⚖️ Filtra per Zavorra:", opzioni_carichi)

                if metodo_selezionato != "Tutti":
                    df_es = df_es[df_es['Metodo'] == metodo_selezionato]
                if attrezzo_selezionato != "Tutti":
                    df_es = df_es[df_es['Attrezzo'] == attrezzo_selezionato]
                if carico_selezionato != "Tutti":
                    if carico_selezionato == "Corpo Libero (0 kg)":
                        df_es = df_es[df_es['Carico_kg'] == 0.0]
                    else:
                        valore_carico = float(carico_selezionato.replace(" kg", ""))
                        df_es = df_es[df_es['Carico_kg'] == valore_carico]

                titolo_progressi = f"### 📈 I Tuoi Progressi: {esercizio_selezionato}"
                if carico_selezionato != "Tutti":
                    titolo_progressi += f" 🎯 [Focus Zavorra: {carico_selezionato}]"
                st.markdown(titolo_progressi)

                st.write("Togli la spunta per escludere gli allenamenti anomali dai grafici (Outliers).")
                
                df_es.insert(0, "Includi", True)
                
                colonne_da_mostrare = ['Includi', 'Data', 'Metodo', 'Attrezzo', 'Resoconto_Auto', 'Note_Esecuzione']
                df_modificato = st.data_editor(
                    df_es[colonne_da_mostrare],
                    column_config={
                        "Includi": st.column_config.CheckboxColumn("📊 Mostra", default=True),
                        "Data": "🗓️ Data",
                        "Metodo": "Metodo",
                        "Attrezzo": "Attrezzo",
                        "Resoconto_Auto": "Esecuzione",
                        "Note_Esecuzione": "Note"
                    },
                    disabled=["Data", "Metodo", "Attrezzo", "Resoconto_Auto", "Note_Esecuzione"], 
                    hide_index=True,
                    use_container_width=True
                )

                df_per_grafici = df_es[df_modificato['Includi'] == True].copy()
                
                if not df_per_grafici.empty:
                    anni_unici = df_per_grafici['Data_Ord'].dt.year.unique()
                    if len(anni_unici) == 1:
                        df_per_grafici['Data_Label'] = df_per_grafici['Data_Ord'].dt.strftime('%d/%m')
                        formato_tooltip = '%d/%m'
                    else:
                        df_per_grafici['Data_Label'] = df_per_grafici['Data_Ord'].dt.strftime('%d/%m/%y')
                        formato_tooltip = '%d/%m/%Y'
                    
                    st.markdown("---")

                    show_carico = (df_per_grafici['Carico_kg'].sum() > 0) and (carico_selezionato == "Tutti")
                    show_emom = df_per_grafici['Metodo'].isin(['EMOM', 'Double EMOM']).any()
                    show_rest = df_per_grafici['Rest_sec'].sum() > 0

                    grafici_attivi = []
                    if show_carico: grafici_attivi.append('carico')
                    if show_emom: grafici_attivi.append('emom')
                    grafici_attivi.append('vol')
                    if show_rest: grafici_attivi.append('rest')

                    def get_x_title(chart_name):
                        return 'Data Allenamento' if grafici_attivi[-1] == chart_name else ''

                    if show_carico:
                        st.markdown("**⚖️ Andamento Carico / Zavorra (kg)**")
                        chart_carico = alt.Chart(df_per_grafici).mark_line(point=True, color='#ff4b4b', size=3).encode(
                            x=alt.X('Data_Label:N', sort=alt.EncodingSortField(field='Data_Ord', order='ascending'), title=get_x_title('carico'), axis=alt.Axis(grid=True, labelAngle=0)),
                            y=alt.Y('Carico_kg:Q', title='Chili (kg)', axis=alt.Axis(grid=True)),
                            tooltip=[alt.Tooltip('Data_Ord:T', title='Data', format=formato_tooltip), alt.Tooltip('Carico_kg:Q', title='Carico (kg)')]
                        )
                        st.altair_chart(chart_carico, use_container_width=True)
                    
                    if show_emom:
                        st.markdown("**⚡ Andamento Reps per Intervallo (Solo EMOM)**")
                        df_emom = df_per_grafici[df_per_grafici['Metodo'].isin(['EMOM', 'Double EMOM'])]
                        chart_emom = alt.Chart(df_emom).mark_line(point=True, color='#ffaa00', size=3).encode(
                            x=alt.X('Data_Label:N', sort=alt.EncodingSortField(field='Data_Ord', order='ascending'), title=get_x_title('emom'), axis=alt.Axis(grid=True, labelAngle=0)),
                            y=alt.Y('Rep_Target:Q', title='Reps', axis=alt.Axis(grid=True)),
                            tooltip=[alt.Tooltip('Data_Ord:T', title='Data', format=formato_tooltip), alt.Tooltip('Rep_Target:Q', title='Reps')]
                        )
                        st.altair_chart(chart_emom, use_container_width=True)

                    st.markdown("**🔄 Andamento Volume Totale (Ripetizioni)**")
                    chart_vol = alt.Chart(df_per_grafici).mark_line(point=True, color='#0068c9', size=3).encode(
                        x=alt.X('Data_Label:N', sort=alt.EncodingSortField(field='Data_Ord', order='ascending'), title=get_x_title('vol'), axis=alt.Axis(grid=True, labelAngle=0)),
                        y=alt.Y('Volume_Totale:Q', title='Volume Totale', axis=alt.Axis(grid=True)),
                        tooltip=[alt.Tooltip('Data_Ord:T', title='Data', format=formato_tooltip), alt.Tooltip('Volume_Totale:Q', title='Reps Totali')]
                    )
                    st.altair_chart(chart_vol, use_container_width=True)
                    
                    if show_rest:
                        st.markdown("**⏱️ Andamento Tempi di Recupero (secondi)**")
                        chart_rest = alt.Chart(df_per_grafici).mark_bar(color='#29b5e8', size=20).encode(
                            x=alt.X('Data_Label:N', sort=alt.EncodingSortField(field='Data_Ord', order='ascending'), title=get_x_title('rest'), axis=alt.Axis(grid=True, labelAngle=0)),
                            y=alt.Y('Rest_sec:Q', title='Secondi', axis=alt.Axis(grid=True)),
                            tooltip=[alt.Tooltip('Data_Ord:T', title='Data', format=formato_tooltip), alt.Tooltip('Rest_sec:Q', title='Recupero (s)')]
                        )
                        st.altair_chart(chart_rest, use_container_width=True)

                else:
                    st.warning("Hai tolto la spunta a tutti gli allenamenti, non c'è nulla da disegnare sui grafici!")

    except Exception as e:
        st.error(f"⚠️ Errore di connessione a Google Sheets: {e}")
