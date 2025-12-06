"""
PDF分析モジュール
"""
from typing import Dict, Any, List
import PyPDF2
import pdfplumber
from pdf2image import convert_from_bytes
import io

def extract_text_from_pdf(pdf_data: bytes) -> str:
    """
    PDFからテキストを抽出
    
    Args:
        pdf_data: PDFデータ
        
    Returns:
        抽出されたテキスト
    """
    try:
        # pdfplumberでテキスト抽出（より高精度）
        with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        
        if text.strip():
            return text
        
        # pdfplumberで取れなかった場合はPyPDF2を試す
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        
        return text
    except Exception as e:
        return f"テキスト抽出エラー: {str(e)}"

def extract_images_from_pdf(pdf_data: bytes, max_pages: int = 10) -> List[bytes]:
    """
    PDFから画像を抽出（各ページを画像として）
    
    Args:
        pdf_data: PDFデータ
        max_pages: 最大ページ数
        
    Returns:
        画像データのリスト
    """
    try:
        # PDFを画像に変換
        images = convert_from_bytes(pdf_data, dpi=150, fmt='jpeg')
        
        image_data_list = []
        for i, image in enumerate(images[:max_pages]):
            # 画像をバイト列に変換
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            image_data_list.append(img_byte_arr.getvalue())
        
        return image_data_list
    except Exception as e:
        return []

def analyze_pdf_content(ai_handler, pdf_data: bytes, system_prompt: str,
                       criteria_sections: list, additional_context: str = "") -> Dict[str, Any]:
    """
    PDFを分析
    
    Args:
        ai_handler: AIハンドラーインスタンス
        pdf_data: PDFデータ
        system_prompt: システムプロンプト
        criteria_sections: 適用する診断基準セクション
        additional_context: 追加の参考情報（企業情報、補足情報など）
        
    Returns:
        分析結果
    """
    # テキスト抽出
    text = extract_text_from_pdf(pdf_data)
    
    # 画像抽出（最大3ページ）
    images = extract_images_from_pdf(pdf_data, max_pages=3)
    
    # テキスト分析
    user_prompt = f"""
【分析対象】
PDFドキュメント

【抽出されたテキスト】
{text[:5000]}  # 最初の5000文字

【適用する診断基準】
{', '.join(criteria_sections)}

【PDFページ数】
約{len(images)}ページ分の画像を抽出

【分析手順】
1. テキスト部分を診断基準に基づいて分析
2. ビジュアル要素（画像から判断）も考慮
3. ドキュメント全体の一貫性をチェック
4. ページごとの問題点を指摘

【重要】
- PDFは複数ページにわたる可能性があるため、全体的な文脈を考慮
- 図表やグラフの説明文にも注意
- 免責事項が小さく書かれていないかチェック
"""
    
    # 追加の参考情報があれば追加
    if additional_context:
        user_prompt += f"\n\n【参考情報】\n{additional_context}\n※上記の参考情報も考慮して解析してください。"
    
    # まずテキストベースで分析
    result = ai_handler.analyze_text(system_prompt, user_prompt)
    
    # 画像がある場合は最初のページの画像も分析
    if images and len(images) > 0:
        image_prompt = """
【補足分析】
PDFの最初のページの画像です。ビジュアル要素（色彩、自然イメージ、シンボル等）を分析してください。
"""
        try:
            image_result = ai_handler.analyze_image(system_prompt, image_prompt, images[0])
            # 画像分析結果をマージ
            if "violations" in image_result and "violations" in result:
                result["violations"].extend(image_result.get("violations", []))
        except:
            pass  # 画像分析が失敗しても続行
    
    return result

def get_pdf_info(pdf_data: bytes) -> Dict[str, Any]:
    """
    PDFの基本情報を取得
    
    Args:
        pdf_data: PDFデータ
        
    Returns:
        PDF情報
    """
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        return {
            "page_count": len(pdf_reader.pages),
            "size_kb": len(pdf_data) / 1024,
            "metadata": pdf_reader.metadata if hasattr(pdf_reader, 'metadata') else {}
        }
    except Exception as e:
        return {
            "error": f"PDF情報の取得に失敗: {str(e)}"
        }
