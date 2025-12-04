"""
Googleスプレッドシート出力モジュール
"""
from typing import Dict, Any
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

class SheetsExporter:
    """Googleスプレッドシートへのエクスポート"""
    
    def __init__(self, credentials_dict: Dict):
        """
        Args:
            credentials_dict: Google Cloud サービスアカウントの認証情報
        """
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.creds = Credentials.from_service_account_info(
            credentials_dict, scopes=scopes
        )
        self.client = gspread.authorize(self.creds)
    
    def export_results(self, spreadsheet_id: str, worksheet_name: str,
                      results: Dict[str, Any]) -> bool:
        """
        診断結果をスプレッドシートに出力
        
        Args:
            spreadsheet_id: スプレッドシートID
            worksheet_name: ワークシート名
            results: 診断結果
            
        Returns:
            成功したかどうか
        """
        try:
            print(f"[DEBUG] スプレッドシート出力開始: {spreadsheet_id}")
            
            # スプレッドシートを開く
            sheet = self.client.open_by_key(spreadsheet_id)
            print(f"[DEBUG] スプレッドシート取得成功: {sheet.title}")
            
            # ワークシートを取得（なければ作成）
            try:
                worksheet = sheet.worksheet(worksheet_name)
                print(f"[DEBUG] ワークシート取得成功: {worksheet_name}")
            except gspread.exceptions.WorksheetNotFound:
                print(f"[DEBUG] ワークシート作成中: {worksheet_name}")
                worksheet = sheet.add_worksheet(
                    title=worksheet_name, 
                    rows=1000, 
                    cols=11  # 11列に修正
                )
                # ヘッダー行を追加
                headers = [
                    "診断日時", "コンテンツタイプ", "診断対象", "適用指令", "診断バージョン",
                    "総合評価", "スコア", "違反項目数", "違反詳細", 
                    "是正提案", "まとめ"
                ]
                worksheet.append_row(headers)
                print(f"[DEBUG] ヘッダー行追加完了")
            
            # データ行を準備
            row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                results.get('content_type', '不明'),
                results.get('content_sample', '')[:500],  # 診断対象（500文字まで）
                results.get('directives', '不明'),
                results.get('version', '不明'),
                results.get('overall_risk', '不明'),
                results.get('score', 0),
                len(results.get('violations', [])),
                self._format_violations(results.get('violations', [])),
                self._format_recommendations(results.get('recommendations', [])),
                results.get('summary', '')[:500]  # 500文字まで
            ]
            
            print(f"[DEBUG] データ行を追加中: {len(row)}列")
            # 行を追加
            worksheet.append_row(row)
            print(f"[DEBUG] データ行追加完了")
            
            return True
        except Exception as e:
            print(f"[ERROR] スプレッドシート出力エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            raise  # エラーを再度投げる
    
    def _format_violations(self, violations: list) -> str:
        """違反項目をフォーマット"""
        if not violations:
            return "なし"
        
        formatted = []
        for v in violations[:5]:  # 最大5件
            formatted.append(
                f"[{v.get('category', '')}] {v.get('category_name', '')}: "
                f"{v.get('description', '')}（減点: {v.get('points_deducted', 0)}）"
            )
        
        if len(violations) > 5:
            formatted.append(f"...他{len(violations) - 5}件")
        
        return " | ".join(formatted)
    
    def _format_recommendations(self, recommendations: list) -> str:
        """是正提案をフォーマット"""
        if not recommendations:
            return "なし"
        
        formatted = []
        for r in recommendations[:3]:  # 最大3件
            formatted.append(
                f"{r.get('issue', '')}: "
                f"{r.get('current_expression', '')} → "
                f"{r.get('recommended_expression', '')}"
            )
        
        if len(recommendations) > 3:
            formatted.append(f"...他{len(recommendations) - 3}件")
        
        return " | ".join(formatted)

def load_credentials_from_streamlit_secrets(st):
    """
    Streamlit Secretsから認証情報を読み込み
    
    Args:
        st: Streamlitモジュール
        
    Returns:
        認証情報の辞書
    """
    try:
        return dict(st.secrets["gcp_service_account"])
    except Exception as e:
        return None
