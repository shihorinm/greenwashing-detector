"""
画像分析モジュール
"""
from typing import Dict, Any
from PIL import Image
import io

def analyze_image_content(ai_handler, image_data: bytes, system_prompt: str,
                         criteria_sections: list, additional_context: str = "") -> Dict[str, Any]:
    """
    画像を分析
    
    Args:
        ai_handler: AIハンドラーインスタンス
        image_data: 画像データ（バイト列）
        system_prompt: システムプロンプト
        criteria_sections: 適用する診断基準セクション
        additional_context: 追加の参考情報（企業情報、補足情報など）
        
    Returns:
        分析結果
    """
    user_prompt = f"""
【分析対象】
提供された画像

【適用する診断基準】
{', '.join(criteria_sections)}

【分析手順】
1. 画像内のテキストを抽出し、テキスト診断を実施
2. ビジュアル要素を以下の観点で分析：
   - 色彩（緑・青・白の使用率）（4.1）
   - 自然イメージ（葉・木・森林・地球・動物・水・空）（4.2）
   - シンボル・アイコン（リサイクルマーク、エコマーク等）（4.3）
   - 製品との関連性（4.4）
3. テキストとビジュアルの整合性を評価
4. 製品の実際の環境性能とイメージのギャップを指摘

【評価ポイント】
- 環境イメージ色の使用率（50%超過でペナルティ）
- 自然イメージと製品の関連性（関連なしは重大違反）
- ミスリーディングなシンボルの使用
- 製品カテゴリーと画像の乖離（例：化石燃料製品+森林画像）
"""
    
    # 追加の参考情報があれば追加
    if additional_context:
        user_prompt += f"\n\n【参考情報】\n{additional_context}\n※上記の参考情報も考慮して解析してください。"
    
    return ai_handler.analyze_image(system_prompt, user_prompt, image_data)

def get_image_info(image_data: bytes) -> Dict[str, Any]:
    """
    画像の基本情報を取得
    
    Args:
        image_data: 画像データ
        
    Returns:
        画像情報
    """
    try:
        image = Image.open(io.BytesIO(image_data))
        return {
            "width": image.width,
            "height": image.height,
            "format": image.format,
            "mode": image.mode,
            "size_kb": len(image_data) / 1024
        }
    except Exception as e:
        return {
            "error": f"画像情報の取得に失敗: {str(e)}"
        }
