"""
ClimateWash解析ツール - メインアプリケーション
"""
import streamlit as st
import sys
import os
from datetime import datetime
import json

# モジュールのインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.ai_handler import AIHandler
from modules.evaluator import evaluate_result, format_result_for_display, calculate_score
from modules.text_analyzer import analyze_text_content, quick_check_text
from modules.image_analyzer import analyze_image_content, get_image_info
from modules.pdf_analyzer import analyze_pdf_content, get_pdf_info
from modules.video_analyzer import analyze_video_content, get_video_info
from modules.web_analyzer import analyze_web_content, get_web_info
from modules.sheets_exporter import SheetsExporter, load_credentials_from_streamlit_secrets
from modules.pdf_reporter import generate_pdf_report
from modules.word_reporter import generate_word_report
from config.criteria import VERSIONS, get_criteria_sections, EXAMPLE_LIBRARY, get_risk_level

def auto_save_to_sheet(result, spreadsheet_id, worksheet_name):
    """
    結果をスプレッドシートに自動保存
    """
    if not spreadsheet_id or not worksheet_name:
        return False
    
    try:
        credentials = load_credentials_from_streamlit_secrets(st)
        if credentials:
            exporter = SheetsExporter(credentials)
            return exporter.export_results(spreadsheet_id, worksheet_name, result)
    except:
        pass
    return False

# ページ設定
st.set_page_config(
    page_title="ClimateWash解析ツール",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if 'diagnosis_history' not in st.session_state:
    st.session_state.diagnosis_history = []
if 'current_result' not in st.session_state:
    st.session_state.current_result = None

def load_system_prompt():
    """システムプロンプトを読み込み"""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    """メインアプリケーション"""
    
    # ヘッダー
    st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #2E7D32 0%, #43A047 100%); border-radius: 10px;'>
        <h1 style='color: white; margin: 0;'>🌍 ClimateWash解析ツール</h1>
        <p style='color: white; margin: 10px 0 0 0;'>EU指令準拠 AI自動解析システム</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # サイドバー設定
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)  # ボタンの上にスペース
        
        # ホームに戻るボタン（リロード機能）
        if st.button("🏠 ホームに戻る", type="primary", use_container_width=True, key="home_sidebar"):
            # すべての状態をクリア
            st.session_state.current_result = None
            st.session_state.show_examples = False
            st.session_state.show_history = False
            st.rerun()
        
        st.markdown("---")
        
        st.markdown("## ⚙️ 設定")
        
        # AI モデル選択
        st.markdown("### AI モデル選択")
        model_type = st.radio(
            "使用するAIモデル",
            ["Claude (Sonnet 4.5)", "ChatGPT (GPT-4)"],
            help="Claude推奨: より詳細な分析が可能"
        )
        
        model_key = "claude" if "Claude" in model_type else "openai"
        
        # API Key取得（Secretsから自動読み込み、なければ手動入力）
        api_key = None
        secret_loaded = False
        
        try:
            if model_key == "claude":
                if "ANTHROPIC_API_KEY" in st.secrets:
                    api_key = st.secrets["ANTHROPIC_API_KEY"]
                    st.success("✅ Anthropic APIキーを自動読み込みしました。")
                    secret_loaded = True
                else:
                    st.info("ℹ️ Secretsに ANTHROPIC_API_KEY が設定されていません")
            elif model_key == "openai":
                if "OPENAI_API_KEY" in st.secrets:
                    api_key = st.secrets["OPENAI_API_KEY"]
                    st.success("✅ OpenAI APIキーを自動読み込みしました。")
                    secret_loaded = True
                else:
                    st.info("ℹ️ Secretsに OPENAI_API_KEY が設定されていません")
        except Exception as e:
            st.warning(f"⚠️ Secrets読み込みエラー: {str(e)}")
        
        # Secretsにない場合は手動入力
        if not api_key:
            st.markdown("### 🔑 API Key")
            api_key = st.text_input(
                f"{'Anthropic' if model_key == 'claude' else 'OpenAI'} API Key",
                type="password",
                help=f"Secretsに設定するか、ここで入力してください",
                key=f"api_key_input_{model_key}"
            )
        
        st.markdown("---")
        
        # 指令選択
        st.markdown("### 📋 適用する指令")
        
        empowerment_directive = st.checkbox(
            "消費者エンパワメント指令（必須）",
            value=True,
            disabled=True,
            help="Directive 2024/825 - 2026年9月27日施行。法的拘束力あり。"
        )
        
        green_claims_directive = st.checkbox(
            "グリーンクレーム指令提案版（推奨）",
            value=True,
            help="COM(2023) 166 - 撤回されたが、実務上のベストプラクティスとして推奨。より詳細な実証・検証要件を含む。"
        )
        
        # 選択に応じた説明
        if green_claims_directive:
            st.info("✅ 両指令を適用: 包括的な解析を実施します。")
        else:
            st.warning("⚠️ エンパワメント指令のみ: 最低限の法令遵守チェックです。")
        
        directive_label = "両指令" if green_claims_directive else "エンパワメント指令のみ"
        
        st.markdown("---")
        
        # バージョン選択
        st.markdown("### 📊 解析基準バージョン")
        
        version_options = {
            "v1": VERSIONS["v1"]["name"],
            "v2": VERSIONS["v2"]["name"],
            "v3": VERSIONS["v3"]["name"]
        }
        
        selected_version = st.radio(
            "バージョン",
            options=list(version_options.keys()),
            format_func=lambda x: version_options[x],
            index=0,  # デフォルトはv1
            help="v1推奨: すべての基準を網羅"
        )
        
        version_info = VERSIONS[selected_version]
        st.caption(version_info["description"])
        
        st.markdown("---")
        
        # スプレッドシート保存の説明
        st.info("📊 解析結果は自動的にGoogleスプレッドシートに保存され、プロジェクトチームに共有されます。")
        
        # スプレッドシートIDをSecretsから自動読み込み（UIなし）
        spreadsheet_id = ""
        worksheet_name = "解析結果"
        
        try:
            if "SPREADSHEET_ID" in st.secrets:
                spreadsheet_id = st.secrets["SPREADSHEET_ID"]
            if "WORKSHEET_NAME" in st.secrets:
                worksheet_name = st.secrets["WORKSHEET_NAME"]
        except:
            pass
        
        st.markdown("---")
        
        # 例文ライブラリ
        if st.button("💡 適切な表現例を見る"):
            st.session_state.show_examples = True
        
        # 解析履歴
        if st.button("📊 解析履歴を見る"):
            st.session_state.show_history = True
        
        st.markdown("---")
        
        # クリアボタン
        st.markdown("### 🗑️ リセット")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("結果クリア", use_container_width=True):
                st.session_state.current_result = None
                st.success("✅ 結果をクリアしました")
                st.rerun()
        with col2:
            if st.button("履歴クリア", use_container_width=True):
                st.session_state.diagnosis_history = []
                st.success("✅ 履歴をクリアしました")
                st.rerun()
    
    # 例文ライブラリの表示
    if st.session_state.get('show_examples', False):
        show_example_library()
        if st.button("🏠 ホームに戻る", type="primary"):
            st.session_state.show_examples = False
            st.rerun()
        return
    
    # 解析履歴の表示
    if st.session_state.get('show_history', False):
        show_diagnosis_history()
        if st.button("🏠 ホームに戻る", type="primary"):
            st.session_state.show_history = False
            st.rerun()
        return
    
    # 解析結果の表示（最優先）
    if st.session_state.get('current_result') is not None:
        display_result(st.session_state.current_result, spreadsheet_id, worksheet_name)
        return
    
    # メインコンテンツ（解析画面）
    tabs = st.tabs(["📝 テキスト", "🖼️ 画像", "📄 PDF", "🎬 動画", "🌐 Webサイト"])
    
    # システムプロンプト読み込み
    system_prompt = load_system_prompt()
    
    # 適用する解析基準セクションを取得
    criteria_sections = get_criteria_sections(selected_version, green_claims_directive)
    
    # タブ1: テキスト解析
    with tabs[0]:
        handle_text_analysis(api_key, model_key, system_prompt, criteria_sections, 
                           selected_version, directive_label, spreadsheet_id, worksheet_name)
    
    # タブ2: 画像解析
    with tabs[1]:
        handle_image_analysis(api_key, model_key, system_prompt, criteria_sections,
                            selected_version, directive_label, spreadsheet_id, worksheet_name)
    
    # タブ3: PDF解析
    with tabs[2]:
        handle_pdf_analysis(api_key, model_key, system_prompt, criteria_sections,
                          selected_version, directive_label, spreadsheet_id, worksheet_name)
    
    # タブ4: 動画解析
    with tabs[3]:
        handle_video_analysis(api_key, model_key, system_prompt, criteria_sections,
                            selected_version, directive_label, spreadsheet_id, worksheet_name)
    
    # タブ5: Webサイト解析
    with tabs[4]:
        handle_web_analysis(api_key, model_key, system_prompt, criteria_sections,
                          selected_version, directive_label, spreadsheet_id, worksheet_name)

def handle_text_analysis(api_key, model_key, system_prompt, criteria_sections, 
                        version, directive_label, spreadsheet_id, worksheet_name):
    """テキスト解析の処理"""
    st.markdown("### 📝 テキスト解析")
    st.markdown("解析したいテキストを入力してください。")
    
    text_input = st.text_area(
        "テキスト入力",
        height=200,
        placeholder="例：当社の製品はカーボンニュートラルです。カーボンオフセットにより実質的なCO2排出をゼロにしています。",
        label_visibility="collapsed"
    )
    
    # リアルタイムプレビュー（簡易チェック）
    if text_input and len(text_input) > 10:
        with st.expander("⚡ クイックチェック（簡易解析）"):
            quick_result = quick_check_text(text_input)
            if quick_result['has_issues']:
                st.warning(f"⚠️ {quick_result['issue_count']}種類の潜在的な問題を検出しました")
                for issue in quick_result['issues']:
                    st.markdown(f"**{issue['type']}**: {', '.join(issue['phrases'])}")
                    st.caption(f"💡 {issue['suggestion']}")
            else:
                st.success("✅ 明らかな問題は検出されませんでした（詳細分析を推奨）")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        diagnose_btn = st.button("🔍 解析開始", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ 入力クリア", use_container_width=True, key="clear_text"):
            st.rerun()
    
    if diagnose_btn:
        if not api_key:
            st.error("❌ APIキーを入力してください")
            return
        
        if not text_input or len(text_input) < 10:
            st.error("❌ 10文字以上のテキストを入力してください")
            return
        
        # 解析実行
        with st.spinner("🔄 AI分析中..."):
            try:
                ai_handler = AIHandler(model_key, api_key)
                ai_response = analyze_text_content(ai_handler, text_input, system_prompt, criteria_sections)
                result = evaluate_result(ai_response)
                
                # 結果を保存
                result['content_type'] = 'テキスト'
                result['version'] = version
                result['directives'] = directive_label
                result['content_sample'] = text_input[:200]
                
                st.session_state.current_result = result
                st.session_state.diagnosis_history.append({
                    'timestamp': datetime.now(),
                    'type': 'テキスト',
                    'result': result
                })
                
                # スプレッドシートに自動保存
                auto_save_to_sheet(result, spreadsheet_id, worksheet_name)
                
                # ページをリロードして結果を表示
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")
                return

def handle_image_analysis(api_key, model_key, system_prompt, criteria_sections,
                         version, directive_label, spreadsheet_id, worksheet_name):
    """画像解析の処理"""
    st.markdown("### 🖼️ 画像解析")
    st.markdown("解析したい画像をアップロードしてください。")
    
    uploaded_file = st.file_uploader(
        "画像ファイル",
        type=['png', 'jpg', 'jpeg', 'webp'],
        help="ドラッグ&ドロップまたはクリックしてファイルを選択",
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        # 画像プレビュー
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)
        
        with col2:
            # 画像情報
            image_data = uploaded_file.read()
            image_info = get_image_info(image_data)
            
            if 'error' not in image_info:
                st.markdown("**画像情報:**")
                st.markdown(f"- サイズ: {image_info['width']} x {image_info['height']}")
                st.markdown(f"- フォーマット: {image_info['format']}")
                st.markdown(f"- ファイルサイズ: {image_info['size_kb']:.1f} KB")
        
        st.markdown("---")
        
        # 必須メモ欄
        image_memo = st.text_area(
            "📝 企業名と、わかれば出所を記入してください。（必須）*",
            placeholder="記入例：●●自動車、公式WEBサイトのトップページ画像／●●株式会社、新幹線の車内広告",
            help="この画像の企業名と出所（Webサイト、広告、パッケージなど）を入力してください。",
            height=80,
            key="image_memo"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            diagnose_btn = st.button("🔍 解析開始", type="primary", use_container_width=True, key="diagnose_image")
        with col2:
            if st.button("🗑️ 画像クリア", use_container_width=True, key="clear_image"):
                st.rerun()
        
        if diagnose_btn:
            if not api_key:
                st.error("❌ APIキーを入力してください")
                return
            
            # メモが空の場合はエラー
            if not image_memo or len(image_memo.strip()) < 5:
                st.error("❌ 企業名と出所を入力してください。（5文字以上）")
                return
            
            # 解析実行
            with st.spinner("🔄 AI分析中（画像解析には少し時間がかかります）..."):
                try:
                    uploaded_file.seek(0)  # ファイルポインタをリセット
                    image_data = uploaded_file.read()
                    
                    ai_handler = AIHandler(model_key, api_key)
                    ai_response = analyze_image_content(ai_handler, image_data, system_prompt, criteria_sections)
                    result = evaluate_result(ai_response)
                    
                    # 結果を保存
                    result['content_type'] = '画像'
                    result['version'] = version
                    result['directives'] = directive_label
                    # メモを記録
                    result['content_sample'] = f"画像: {uploaded_file.name} | {image_memo}"
                    
                    st.session_state.current_result = result
                    st.session_state.diagnosis_history.append({
                        'timestamp': datetime.now(),
                        'type': '画像',
                        'result': result
                    })
                    
                    # スプレッドシートに自動保存
                    auto_save_to_sheet(result, spreadsheet_id, worksheet_name)
                    
                    # ページをリロードして結果を表示
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
                    return

def handle_pdf_analysis(api_key, model_key, system_prompt, criteria_sections,
                       version, directive_label, spreadsheet_id, worksheet_name):
    """PDF解析の処理"""
    st.markdown("### 📄 PDF解析")
    st.markdown("解析したいPDFをアップロードしてください。")
    
    uploaded_file = st.file_uploader(
        "PDFファイル",
        type=['pdf'],
        help="テキストと画像を自動抽出して分析します",
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        # PDF情報
        pdf_data = uploaded_file.read()
        pdf_info = get_pdf_info(pdf_data)
        
        if 'error' not in pdf_info:
            st.markdown("**PDF情報:**")
            st.markdown(f"- ページ数: {pdf_info['page_count']}")
            st.markdown(f"- ファイルサイズ: {pdf_info['size_kb']:.1f} KB")
        
        st.markdown("---")
        
        # 必須メモ欄
        pdf_memo = st.text_area(
            "📝 企業名と、わかれば出所を記入してください。（必須）*",
            placeholder="記入例：●●株式会社、プレスリリース／●●銀行、サステナビリティレポート",
            help="このPDFの企業名と出所（報告書名、資料名など）を入力してください。",
            height=80,
            key="pdf_memo"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            diagnose_btn = st.button("🔍 解析開始", type="primary", use_container_width=True, key="diagnose_pdf")
        with col2:
            if st.button("🗑️ PDFクリア", use_container_width=True, key="clear_pdf"):
                st.rerun()
        
        if diagnose_btn:
            if not api_key:
                st.error("❌ APIキーを入力してください")
                return
            
            # メモが空の場合はエラー
            if not pdf_memo or len(pdf_memo.strip()) < 5:
                st.error("❌ 企業名と出所を入力してください。（5文字以上）")
                return
            
            # 解析実行
            with st.spinner("🔄 AI分析中（PDFの処理には時間がかかります）..."):
                try:
                    uploaded_file.seek(0)
                    pdf_data = uploaded_file.read()
                    
                    ai_handler = AIHandler(model_key, api_key)
                    ai_response = analyze_pdf_content(ai_handler, pdf_data, system_prompt, criteria_sections)
                    result = evaluate_result(ai_response)
                    
                    result['content_type'] = 'PDF'
                    result['version'] = version
                    result['directives'] = directive_label
                    # メモを記録
                    result['content_sample'] = f"PDF: {uploaded_file.name} | {pdf_memo}"
                    
                    st.session_state.current_result = result
                    st.session_state.diagnosis_history.append({
                        'timestamp': datetime.now(),
                        'type': 'PDF',
                        'result': result
                    })
                    
                    # スプレッドシートに自動保存
                    auto_save_to_sheet(result, spreadsheet_id, worksheet_name)
                    
                    # ページをリロードして結果を表示
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
                    return
            

def handle_video_analysis(api_key, model_key, system_prompt, criteria_sections,
                         version, directive_label, spreadsheet_id, worksheet_name):
    """動画解析の処理"""
    st.markdown("### 🎬 動画解析")
    st.markdown("解析したい動画をアップロードしてください（最長60秒まで処理）。")
    st.info("💡 YouTube動画を解析したい場合は、事前にダウンロードしてからアップロードしてください。")
    
    uploaded_file = st.file_uploader(
        "動画ファイル",
        type=['mp4', 'mov', 'avi'],
        help="1秒ごとにフレームをキャプチャして分析します",
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        video_data = uploaded_file.read()
        
        # 動画情報
        video_info = get_video_info(video_data)
        
        if 'error' not in video_info:
            st.markdown("**動画情報:**")
            st.markdown(f"- 長さ: {video_info['duration_seconds']:.1f}秒")
            st.markdown(f"- 解像度: {video_info['width']} x {video_info['height']}")
            st.markdown(f"- ファイルサイズ: {video_info['size_mb']:.1f} MB")
            
            if video_info['duration_seconds'] > 60:
                st.warning("⚠️ 動画が60秒を超えています。最初の60秒のみ分析されます。")
        
        st.markdown("---")
        
        # 必須メモ欄
        video_memo = st.text_area(
            "📝 企業名と、わかれば出所を記入してください。（必須）*",
            placeholder="記入例：●●化粧品、WEBの動画広告／●●不動産、テレビCM（××放送）",
            help="この動画の企業名と出所（CM名、YouTube、イベント名など）を入力してください。",
            height=80,
            key="video_memo"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            diagnose_btn = st.button("🔍 解析開始", type="primary", use_container_width=True, key="diagnose_video")
        with col2:
            if st.button("🗑️ 動画クリア", use_container_width=True, key="clear_video"):
                st.rerun()
        
        if diagnose_btn:
            if not api_key:
                st.error("❌ APIキーを入力してください")
                return
            
            # メモが空の場合はエラー
            if not video_memo or len(video_memo.strip()) < 5:
                st.error("❌ 企業名と出所を入力してください。（5文字以上）")
                return
            with st.spinner("🔄 AI分析中（動画の処理には時間がかかります）..."):
                try:
                    ai_handler = AIHandler(model_key, api_key)
                    ai_response = analyze_video_content(ai_handler, video_data, system_prompt, criteria_sections)
                    result = evaluate_result(ai_response)
                    
                    result['content_type'] = '動画'
                    result['version'] = version
                    result['directives'] = directive_label
                    # メモを記録
                    result['content_sample'] = f"動画: {uploaded_file.name} | {video_memo}"
                    
                    st.session_state.current_result = result
                    st.session_state.diagnosis_history.append({
                        'timestamp': datetime.now(),
                        'type': '動画',
                        'result': result
                    })
                    
                    # スプレッドシートに自動保存
                    auto_save_to_sheet(result, spreadsheet_id, worksheet_name)
                    
                    # ページをリロードして結果を表示
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
                    return
            

def handle_web_analysis(api_key, model_key, system_prompt, criteria_sections,
                       version, directive_label, spreadsheet_id, worksheet_name):
    """Webサイト解析の処理"""
    st.markdown("### 🌐 Webサイト解析")
    st.markdown("解析したいWebサイトのURLを入力してください。")
    
    url_input = st.text_input(
        "URL",
        placeholder="https://example.com/sustainability",
        label_visibility="collapsed"
    )
    
    if url_input:
        # URL検証
        if not url_input.startswith(('http://', 'https://')):
            st.warning("⚠️ URLは http:// または https:// で始める必要があります")
            return
        
        # Webサイト情報を取得
        with st.expander("🔍 サイト情報を確認"):
            with st.spinner("情報取得中..."):
                web_info = get_web_info(url_input)
                
                if 'error' not in web_info:
                    st.markdown(f"**タイトル**: {web_info['title']}")
                    st.markdown(f"**説明**: {web_info['description'][:200]}...")
                    st.markdown(f"**テキスト量**: {web_info['text_length']}文字")
                    st.markdown(f"**画像数**: {web_info['image_count']}枚")
                else:
                    st.error(f"情報取得失敗: {web_info['error']}")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            diagnose_btn = st.button("🔍 解析開始", type="primary", use_container_width=True, key="diagnose_web")
        with col2:
            if st.button("🗑️ URLクリア", use_container_width=True, key="clear_web"):
                st.rerun()
        
        if diagnose_btn:
            if not api_key:
                st.error("❌ APIキーを入力してください")
                return
            
            # 解析実行
            with st.spinner("🔄 AI分析中（Webページの処理には時間がかかります）..."):
                try:
                    ai_handler = AIHandler(model_key, api_key)
                    ai_response = analyze_web_content(ai_handler, url_input, system_prompt, criteria_sections)
                    result = evaluate_result(ai_response)
                    
                    result['content_type'] = 'Webサイト'
                    result['version'] = version
                    result['directives'] = directive_label
                    result['content_sample'] = url_input
                    
                    st.session_state.current_result = result
                    st.session_state.diagnosis_history.append({
                        'timestamp': datetime.now(),
                        'type': 'Webサイト',
                        'result': result
                    })
                    
                    # スプレッドシートに自動保存
                    auto_save_to_sheet(result, spreadsheet_id, worksheet_name)
                    
                    # ページをリロードして結果を表示
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
                    return
            

def display_result(result, spreadsheet_id, worksheet_name):
    """解析結果を表示"""
    st.markdown("---")
    st.markdown("## 📊 解析結果")
    
    if not result.get('success', False):
        st.error(f"❌ {result.get('error', '不明なエラー')}")
        if 'details' in result:
            st.error(result['details'])
        return
    
    # 総合評価
    risk_info = result.get('risk_info', {})
    color = risk_info.get('color', '')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総合評価", f"{color} {result['overall_risk']}")
    with col2:
        st.metric("スコア", f"{result['score']}/100")
    with col3:
        st.metric("違反項目数", f"{len(result['violations'])}件")
    
    st.info(f"📝 {risk_info.get('description', '')}")
    
    # 詳細結果
    formatted_result = format_result_for_display(result)
    st.markdown(formatted_result)
    
    # アクション
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # PDFダウンロード
        try:
            pdf_data = generate_pdf_report(result)
            st.download_button(
                label="📄 PDF",
                data=pdf_data,
                file_name=f"climatewash_report_{datetime.now():%Y%m%d_%H%M%S}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"pdf_{id(result)}"
            )
        except Exception as e:
            st.error(f"PDFエラー: {str(e)}")
    
    with col2:
        # Wordダウンロード
        try:
            word_data = generate_word_report(result)
            st.download_button(
                label="📝 Word",
                data=word_data,
                file_name=f"climatewash_report_{datetime.now():%Y%m%d_%H%M%S}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key=f"word_{id(result)}"
            )
        except Exception as e:
            st.error(f"Wordエラー: {str(e)}")
    
    with col3:
        # JSON結果をダウンロード
        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON",
            data=result_json,
            file_name=f"climatewash_result_{datetime.now():%Y%m%d_%H%M%S}.json",
            mime="application/json",
            use_container_width=True,
            key=f"json_{id(result)}"
        )
    
    # スプレッドシート自動保存通知
    if spreadsheet_id and worksheet_name:
        st.success("✅ この結果はスプレッドシートに自動保存されました")
    
    # HOMEボタン
    st.markdown("---")
    if st.button("🏠 ホームに戻る", type="primary", use_container_width=False, key=f"home_{id(result)}"):
        st.session_state.current_result = None
        st.rerun()

def show_example_library():
    """例文ライブラリを表示"""
    st.markdown("## 💡 適切な表現例ライブラリ")
    st.markdown("EU指令に準拠した適切な表現例を参照できます。")
    
    for category, examples in EXAMPLE_LIBRARY.items():
        with st.expander(f"📚 {category}"):
            for i, example in enumerate(examples, 1):
                st.markdown(f"### 例 {i}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**❌ NG表現:**")
                    st.error(example['ng'])
                
                with col2:
                    st.markdown("**✅ OK表現:**")
                    st.success(example['ok'])
                
                st.markdown(f"**📝 理由:** {example['reason']}")
                st.markdown("---")

def show_diagnosis_history():
    """解析履歴を表示"""
    st.markdown("## 📊 解析履歴")
    
    if not st.session_state.diagnosis_history:
        st.info("まだ解析履歴がありません。")
        return
    
    # 履歴を時系列で表示
    history = sorted(st.session_state.diagnosis_history, 
                    key=lambda x: x['timestamp'], reverse=True)
    
    # 統計情報
    st.markdown("### 📈 統計")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("総解析数", len(history))
    
    with col2:
        avg_score = sum(h['result']['score'] for h in history) / len(history)
        st.metric("平均スコア", f"{avg_score:.1f}")
    
    with col3:
        high_risk_count = sum(1 for h in history if h['result']['overall_risk'] == 'High Risk')
        st.metric("High Risk件数", high_risk_count)
    
    with col4:
        type_counts = {}
        for h in history:
            t = h['type']
            type_counts[t] = type_counts.get(t, 0) + 1
        most_common = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "なし"
        st.metric("最多解析タイプ", most_common)
    
    st.markdown("---")
    
    # 履歴リスト
    st.markdown("### 📋 解析リスト")
    
    for i, entry in enumerate(history):
        timestamp = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        result = entry['result']
        
        with st.expander(f"{timestamp} - {entry['type']} - {result['overall_risk']} ({result['score']}点)"):
            st.markdown(format_result_for_display(result))

if __name__ == "__main__":
    main()
