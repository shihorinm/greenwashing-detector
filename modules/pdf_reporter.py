"""
PDFレポート生成モジュール
"""
from typing import Dict, Any
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

def generate_pdf_report(results: Dict[str, Any]) -> bytes:
    """
    診断結果からPDFレポートを生成
    
    Args:
        results: 診断結果
        
    Returns:
        PDFデータ（バイト列）
    """
    # 日本語フォントを登録
    try:
        # Noto Sans JPフォントを登録（システムにある場合）
        pdfmetrics.registerFont(TTFont('Japanese', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', subfontIndex=0))
        japanese_font = 'Japanese'
    except:
        try:
            # IPAフォントを試す
            pdfmetrics.registerFont(TTFont('Japanese', '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'))
            japanese_font = 'Japanese'
        except:
            # フォントが見つからない場合はデフォルトを使用（文字化けする可能性あり）
            japanese_font = 'Helvetica'
    
    # メモリ上にPDFを作成
    buffer = io.BytesIO()
    
    # PDFドキュメントを作成
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # ストーリー（コンテンツ）を準備
    story = []
    
    # スタイルを取得
    styles = getSampleStyleSheet()
    
    # カスタムスタイルを追加（日本語フォント使用）
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=japanese_font,
        fontSize=24,
        textColor=colors.HexColor('#2E7D32'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=japanese_font,
        fontSize=16,
        textColor=colors.HexColor('#2E7D32'),
        spaceAfter=12
    )
    
    # 本文用の日本語スタイル
    normal_style = ParagraphStyle(
        'JapaneseNormal',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=11,
        leading=16
    )
    
    # タイトルページ
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("ClimateWash診断レポート", title_style))
    story.append(Spacer(1, 1*cm))
    
    # 診断日時
    report_date = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    story.append(Paragraph(f"診断日時: {report_date}", normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # コンテンツタイプ
    content_type = results.get('content_type', '不明')
    story.append(Paragraph(f"コンテンツタイプ: {content_type}", normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 診断対象
    content_sample = results.get('content_sample', '')
    if content_sample:
        story.append(Paragraph(f"診断対象: {content_sample}", normal_style))
        story.append(Spacer(1, 2*cm))
    else:
        story.append(Spacer(1, 2*cm))
    
    # ページブレイク
    story.append(PageBreak())
    
    # サマリーセクション
    story.append(Paragraph("診断サマリー", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    # サマリーテーブル
    risk_level = results.get('overall_risk', '不明')
    score = results.get('score', 0)
    risk_info = results.get('risk_info', {})
    
    risk_color_map = {
        "High Risk": colors.red,
        "Medium Risk": colors.orange,
        "Low Risk": colors.yellow,
        "Compliant": colors.green
    }
    
    risk_color = risk_color_map.get(risk_level, colors.grey)
    
    summary_data = [
        [Paragraph("項目", normal_style), Paragraph("内容", normal_style)],
        [Paragraph("総合評価", normal_style), Paragraph(risk_level, normal_style)],
        [Paragraph("スコア", normal_style), Paragraph(f"{score}/100", normal_style)],
        [Paragraph("適用指令", normal_style), Paragraph(results.get('directives', '不明'), normal_style)],
        [Paragraph("診断バージョン", normal_style), Paragraph(results.get('version', '不明'), normal_style)],
        [Paragraph("違反項目数", normal_style), Paragraph(f"{len(results.get('violations', []))}件", normal_style)]
    ]
    
    summary_table = Table(summary_data, colWidths=[6*cm, 10*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), japanese_font),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (1, 1), (1, 1), risk_color),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 1*cm))
    
    # 評価説明
    description = risk_info.get('description', '')
    story.append(Paragraph(f"<b>評価:</b> {description}", normal_style))
    story.append(Spacer(1, 1*cm))
    
    # まとめ
    story.append(Paragraph("総括", heading_style))
    summary_text = results.get('summary', '')
    story.append(Paragraph(summary_text, normal_style))
    story.append(Spacer(1, 1*cm))
    
    # ページブレイク
    story.append(PageBreak())
    
    # 違反項目セクション
    violations = results.get('violations', [])
    if violations:
        story.append(Paragraph(f"検出された問題点 ({len(violations)}件)", heading_style))
        story.append(Spacer(1, 0.5*cm))
        
        for i, violation in enumerate(violations, 1):
            # 違反項目のタイトル
            v_title = f"{i}. {violation.get('category_name', '不明な項目')} (項目 {violation.get('category', '')})"
            story.append(Paragraph(f"<b>{v_title}</b>", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            # 詳細テーブル（Paragraphでラップして折り返し対応）
            v_data = [
                [Paragraph("リスクレベル", normal_style), Paragraph(violation.get('risk_level', 'Unknown'), normal_style)],
                [Paragraph("減点", normal_style), Paragraph(f"{violation.get('points_deducted', 0)}点", normal_style)],
                [Paragraph("問題内容", normal_style), Paragraph(violation.get('description', ''), normal_style)],
                [Paragraph("該当表現", normal_style), Paragraph(violation.get('evidence', ''), normal_style)]
            ]
            
            v_table = Table(v_data, colWidths=[4*cm, 12*cm])
            v_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, -1), japanese_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            story.append(v_table)
            story.append(Spacer(1, 0.7*cm))
    else:
        story.append(Paragraph("検出された問題点", heading_style))
        story.append(Paragraph("問題は検出されませんでした。", normal_style))
        story.append(Spacer(1, 1*cm))
    
    # ページブレイク
    story.append(PageBreak())
    
    # 是正提案セクション
    recommendations = results.get('recommendations', [])
    if recommendations:
        story.append(Paragraph(f"是正提案 ({len(recommendations)}件)", heading_style))
        story.append(Spacer(1, 0.5*cm))
        
        for i, rec in enumerate(recommendations, 1):
            # 提案のタイトル
            r_title = f"{i}. {rec.get('issue', '問題')}"
            story.append(Paragraph(f"<b>{r_title}</b>", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            # 現在の表現
            current = rec.get('current_expression', '')
            story.append(Paragraph(f"<b>現在の表現:</b> 「{current[:150]}」", normal_style))
            story.append(Spacer(1, 0.2*cm))
            
            # 推奨する表現
            recommended = rec.get('recommended_expression', '')
            story.append(Paragraph(f"<b>推奨する表現:</b> 「{recommended[:150]}」", normal_style))
            story.append(Spacer(1, 0.2*cm))
            
            # 理由
            explanation = rec.get('explanation', '')
            story.append(Paragraph(f"<b>理由:</b> {explanation[:200]}", normal_style))
            story.append(Spacer(1, 0.7*cm))
    else:
        story.append(Paragraph("是正提案", heading_style))
        story.append(Paragraph("是正の必要はありません。", normal_style))
        story.append(Spacer(1, 1*cm))
    
    # PDFを構築
    doc.build(story)
    
    # バイト列を取得
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data
