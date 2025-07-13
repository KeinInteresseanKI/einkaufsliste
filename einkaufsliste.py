import streamlit as st
import pandas as pd
import datetime

# from streamlit_gsheets.gsheets_connection import GSheetsConnection  # この行は削除
# from st_gsheets_connection.connection import GSheetsConnection  # この行も削除

st.set_page_config(page_title='EINKAUFSLISTE', page_icon='🛒')

# --- 商品リスト（定数） ---
sp_item = ['トマト', '人参', 'レタス','ねぎ','ラディッシュ','タマネギ','牛乳','たまご',
           'Frischkäse', '砂糖', '塩', 'こしょう / つぶ', 'こしょう / 粉', '食器洗剤', 'コンソメ - Penny']
jp_item = ['しょうゆ', 'ごま油', '牡蠣ソース', 'みりん', 'テンメンジャン', 'サンバル']

# --- Google Sheets 読み込み ---
# st.connection() を使用し、type="gsheets" を指定します
conn = st.connection("gsheets", type="gsheets")

# --- DBの読み込み (キャッシュを無効化) ---
@st.cache_data(ttl=5)
def load_df():
    df = conn.read(worksheet="EINKAUF", usecols=list(range(2)))

    if df.empty or not all(col in df.columns for col in ["item", "date"]):
        return pd.DataFrame(columns=["item", "date"])

    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    return df

# --- ヘルパー関数: Google Sheetsを更新し、キャッシュをクリアして再読み込み ---
def update_gsheet_and_rerun(df_to_write):
    conn.update(worksheet="EINKAUF", data=df_to_write)
    st.cache_data.clear()
    st.rerun()

def add_item(item):
    df = load_df()
    today = datetime.date.today().isoformat()
    new_row = pd.DataFrame([[item, today]], columns=["item", "date"])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    update_gsheet_and_rerun(updated_df)

def update_item(idx, new_item):
    df = load_df()
    df.loc[idx, "item"] = new_item
    if 'edit_idx' in st.session_state:
        del st.session_state.edit_idx 
    update_gsheet_and_rerun(df)

def delete_item(idx):
    df = load_df()
    df = df.drop(index=idx).reset_index(drop=True)
    if 'del_idx' in st.session_state:
        del st.session_state.del_idx
    update_gsheet_and_rerun(df)

def clear_all():
    empty_df = pd.DataFrame(columns=["item", "date"])
    update_gsheet_and_rerun(empty_df)

# --- アプリ UI ---
df = load_df()
st.title('🛒 EINKAUFSLISTE')

st.header("🧾 AKTUELLE LISTE")
if df.empty:
    st.info("Noch kein Item in der Liste")
else:
    for i, row in df.iterrows():
        col1, col2, col3 = st.columns([1.2, 0.8, 2])
        with col1:
            st.checkbox(f"{row['item']}", key=f"cb_{row['item']}_{i}")
        with col2:
            if st.button('✍️ Änderung', key=f'edit_{i}'):
                st.session_state.edit_idx = i
                st.rerun()
        with col3:
            if st.button('👋 Löschen', key=f'del_{i}'):
                st.session_state.del_idx = i
                st.rerun()

if 'edit_idx' in st.session_state and st.session_state.edit_idx is not None:
    i = st.session_state.edit_idx
    if i in df.index:
        st.markdown("---")
        old_item = df.at[i, "item"]
        st.subheader(f'✍️ ÄNDERUNG: {old_item}')
        ae_re_od_ir = st.radio('Reguläres oder Irreguläres Item',
                                 ['Reguläres - Supermarkt neu', 'Reguläres - JP-Laden neu', 'Sonstiges neu'],
                                 horizontal=True, key=f'edit_radio_{i}')

        new_item = None
        if ae_re_od_ir == 'Reguläres - Supermarkt neu':
            new_item = st.selectbox(f'Neues Item auswählen - Aktuell: {old_item}', sp_item, index=None, placeholder='Supermarkt-Item auswählen', key=f'edit_sp_select_{i}')
        elif ae_re_od_ir == 'Reguläres - JP-Laden neu':
            new_item = st.selectbox(f'Neues Item auswählen - Aktuell: {old_item}', jp_item, index=None, placeholder='JP-Laden-Item auswählen', key=f'edit_jp_select_{i}')
        else:
            new_item = st.text_input(f'Neues Item eingeben - Aktuell: {old_item}', placeholder='Item eingeben', key=f'edit_text_input_{i}')

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button('👌 Ändern', key=f'confirm_edit_{i}') and new_item:
                update_item(i, new_item)
        with col2:
            if st.button('👎 Abbrechen', key=f'cancel_edit_{i}'):
                del st.session_state.edit_idx
                st.rerun()

if 'del_idx' in st.session_state and st.session_state.del_idx is not None:
    i = st.session_state.del_idx
    if i in df.index:
        st.markdown("---")
        st.subheader(f"👋 Löschen: {df.at[i, 'item']}?")
        col1, col2 = st.columns([1,4])
        with col1:
            if st.button('👌 Löschen', key=f'confirm_del_{i}'):
                delete_item(i)
        with col2:        
            if st.button('👎 Abbrechen', key=f'cancel_del_{i}'):
                del st.session_state.del_idx
                st.rerun()

st.markdown("---")

st.subheader('✏️ Neues Item hinzufügen')
re_od_ir = st.radio('Reguläres oder Irreguläres Item',
                     ['Reguläres - Supermarkt', 'Reguläres - JP-Laden', 'Sonstiges'],
                     horizontal=True, key='add_radio')
item = None
if re_od_ir == 'Reguläres - Supermarkt':
    item = st.selectbox('Item auswählen', sp_item, index=None, placeholder='Supermarkt-Item auswählen', key='add_sp_select')
elif re_od_ir == 'Reguläres - JP-Laden':
    item = st.selectbox('Item auswählen', jp_item, index=None, placeholder='JP-Laden-Item auswählen', key='add_jp_select')
else:
    item = st.text_input('Item eingeben', placeholder='Item eingeben', key='add_text_input')

if st.button('Hinzufügen') and item:
    add_item(item)

st.markdown("---")
st.subheader('🧹 Liste leeren')
confirm = st.radio('Liste leeren?', ['Nein', 'Ja'], horizontal=True, index=0, key='clear_radio')
if st.button('🧹 Leeren') and confirm == 'Ja':
    clear_all()
elif confirm == 'Nein':
    st.info('Die Liste wird nicht geleert.')
