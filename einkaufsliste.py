import streamlit as st
import pandas as pd
import datetime

# --- streamlit_gsheets.gsheets_connection は不要になるため削除 ---
# from streamlit_gsheets.gsheets_connection import GSheetsConnection

st.set_page_config(page_title='EINKAUFSLISTE', page_icon='🛒')

# --- 商品リスト（定数） ---
sp_item = ['トマト', '人参', 'レタ','ねぎ','ラディッシュ','タマネギ','牛乳','たまご',
           'Frischkäse', '砂糖', '塩', 'こしょう / つぶ', 'こしょう / 粉', '食器洗剤', 'コンソメ - Penny']
jp_item = ['しょうゆ', 'ごま油', '牡蠣ソース', 'みりん', 'テンメンジャン', 'サンバル']

# --- Google Sheets 読み込み ---
# type="gsheets" を指定することで、Streamlitが内部で適切なGoogle Sheetsコネクタを使用します
conn = st.connection("gsheets", type="gsheets")

# --- DBの読み込み (キャッシュを無効化) ---
@st.cache_data(ttl=5) # データの鮮度を保つために短めのTTLを設定
def load_df():
    # キャッシュをクリアして常に最新のデータを読み込む (関数内ではなく、更新関数でクリア)
    # usecolsを指定する場合、ヘッダーも考慮して適切な列数を指定
    df = conn.read(worksheet="EINKAUF", usecols=list(range(2))) 
    
    # データが空の場合、または必要な列がない場合は、空のDataFrameを返す
    # GSheetsコネクタは通常、ヘッダーを自動認識するため、手動でのヘッダースキップは不要なことが多い
    if df.empty or not all(col in df.columns for col in ["item", "date"]):
        return pd.DataFrame(columns=["item", "date"])
    
    # 'date' 列を日付型に変換。無効な値はNaT（Not a Time）になる
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    return df

# --- ヘルパー関数: Google Sheetsを更新し、キャッシュをクリアして再読み込み ---
def update_gsheet_and_rerun(df_to_write):
    # Google Sheetsにデータを書き込む
    # Streamlit GSheetsコネクタはDataFrameをそのまま書き込むのが最も簡単です
    conn.update(worksheet="EINKAUF", data=df_to_write)
    
    # キャッシュをクリアして最新のデータを強制的に再読み込み
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
    if 'edit_idx' in st.session_state: # 存在チェックを追加
        del st.session_state.edit_idx 
    update_gsheet_and_rerun(df)

def delete_item(idx):
    df = load_df()
    # ドロップ後のインデックスをリセットすることで、Google Sheetsへの書き込み時に問題が起きないようにする
    df = df.drop(index=idx).reset_index(drop=True)
    if 'del_idx' in st.session_state: # 存在チェックを追加
        del st.session_state.del_idx
    update_gsheet_and_rerun(df)

def clear_all():
    empty_df = pd.DataFrame(columns=["item", "date"])
    update_gsheet_and_rerun(empty_df)



## 🛒 EINKAUFSLISTE


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
                st.rerun() # 編集モードに入ったらすぐにUIを更新
        with col3:
            if st.button('👋 Löschen', key=f'del_{i}'):
                st.session_state.del_idx = i
                st.rerun() # 削除モードに入ったらすぐにUIを更新

# 編集・削除フォームの表示は、セッションステートの変更後にのみ行う
if 'edit_idx' in st.session_state and st.session_state.edit_idx is not None:
    i = st.session_state.edit_idx
    if i in df.index: # 削除後に編集しようとした場合の対策
        st.markdown("---")
        old_item = df.at[i, "item"]
        st.subheader(f'✍️ ÄNDERUNG: {old_item}')
        ae_re_od_ir = st.radio('Reguläres oder Irreguläres Item',
                                 ['Reguläres - Supermarkt neu', 'Reguläres - JP-Laden neu', 'Sonstiges neu'],
                                 horizontal=True, key=f'edit_radio_{i}')
        
        new_item = None # 初期値をNoneに設定
        if ae_re_od_ir == 'Reguläres - Supermarkt neu':
            new_item = st.selectbox(f'Neues Item auswählen - Aktuell: {old_item}', sp_item, index=None, placeholder='Supermarkt-Item auswählen', key=f'edit_sp_select_{i}')
        elif ae_re_od_ir == 'Reguläres - JP-Laden neu':
            new_item = st.selectbox(f'Neues Item auswählen - Aktuell: {old_item}', jp_item, index=None, placeholder='JP-Laden-Item auswählen', key=f'edit_jp_select_{i}')
        else:
            new_item = st.text_input(f'Neues Item eingeben - Aktuell: {old_item}', placeholder='Item eingeben', key=f'edit_text_input_{i}')
        
        col1, col2 = st.columns([1, 4])
        with col1:
            # new_itemがNoneまたは空文字列の場合にボタンを押せないようにする
            if st.button('👌 Ändern', key=f'confirm_edit_{i}') and new_item: 
                update_item(i, new_item)
        with col2:
            if st.button('👎 Abbrechen', key=f'cancel_edit_{i}'):
                del st.session_state.edit_idx
                st.rerun()

if 'del_idx' in st.session_state and st.session_state.del_idx is not None:
    i = st.session_state.del_idx
    if i in df.index: # 削除後に削除しようとした場合の対策
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
                     horizontal=True, key='add_radio') # キーを追加
item = None # 初期値をNoneに設定
if re_od_ir == 'Reguläres - Supermarkt':
    item = st.selectbox('Item auswählen', sp_item, index=None, placeholder='Supermarkt-Item auswählen', key='add_sp_select') # キーを追加
elif re_od_ir == 'Reguläres - JP-Laden':
    item = st.selectbox('Item auswählen', jp_item, index=None, placeholder='JP-Laden-Item auswählen', key='add_jp_select') # キーを追加
else:
    item = st.text_input('Item eingeben', placeholder='Item eingeben', key='add_text_input') # キーを追加

if st.button('Hinzufügen') and item: # itemがNoneまたは空文字列でない場合のみ実行
    add_item(item)

st.markdown("---")
st.subheader('🧹 Liste leeren')
confirm = st.radio('Liste leeren?', ['Nein', 'Ja'], horizontal=True, index=0, key='clear_radio') # キーを追加
if st.button('🧹 Leeren') and confirm == 'Ja':
    clear_all()
elif confirm == 'Nein': # 「Ja」を選んでいない場合のみ表示
    st.info('Die Liste wird nicht geleert.')
