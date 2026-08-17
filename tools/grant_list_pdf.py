#!/usr/bin/env python3
"""1920x1080 grant checklist PDF for Takae / UNGR ARCHIVE (2026-08)."""
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white, black
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT = "JP"
pdfmetrics.registerFont(
    TTFont(FONT, "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", subfontIndex=0)
)

W, H = 1920, 1080
BG = HexColor("#F4F4F2")
INK = HexColor("#111111")
MUTED = HexColor("#5A5A5A")
LINE = HexColor("#D0D0D0")
RED = HexColor("#C41E3A")
ACCENT = HexColor("#111111")
PILL_HI = HexColor("#111111")
PILL_MID = HexColor("#4A4A4A")
PILL_LO = HexColor("#8A8A8A")


def sw(text, size):
    return pdfmetrics.stringWidth(text, FONT, size)


def wrap(text, size, maxw):
    lines = []
    for para in str(text).split("\n"):
        if not para:
            lines.append("")
            continue
        buf = ""
        for ch in para:
            if sw(buf + ch, size) <= maxw:
                buf += ch
            else:
                lines.append(buf)
                buf = ch
        if buf:
            lines.append(buf)
    return lines


def draw_wrap(c, text, x, y, size, maxw, color=INK, leading=None, max_lines=None):
    leading = leading or size * 1.38
    lines = wrap(text, size, maxw)
    if max_lines and len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [lines[max_lines - 1][: max(1, len(lines[max_lines - 1]) - 1)] + "…"]
    c.setFillColor(color)
    c.setFont(FONT, size)
    for i, line in enumerate(lines):
        c.drawString(x, y - i * leading, line)
    return len(lines) * leading


def header(c, page, total, kicker=""):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(INK)
    c.rect(0, H - 8, W, 8, fill=1, stroke=0)
    c.setFont(FONT, 14)
    c.setFillColor(MUTED)
    c.drawString(56, H - 42, "UNGR ARCHIVE  /  助成・補助金チェックリスト  2026-08")
    if kicker:
        c.setFillColor(INK)
        c.setFont(FONT, 14)
        c.drawRightString(W - 56, H - 42, kicker)
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(56, H - 56, W - 56, H - 56)
    c.setFillColor(MUTED)
    c.setFont(FONT, 13)
    c.drawString(56, 32, "日本国内  /  映画・撮影・AI・IT  /  判定は2026年8月時点の公開情報＋本人プロフィール")
    c.drawRightString(W - 56, 32, f"{page} / {total}")


def pct_color(p):
    if p >= 45:
        return HexColor("#1A7A3A")
    if p >= 25:
        return HexColor("#B36B00")
    return RED


GRANTS = [
    {
        "no": 1,
        "cat": "AI / IT",
        "name": "デジタル化・AI導入補助金2026（通常枠）旧IT導入補助金",
        "pct": 52,
        "why": "従業員ゼロでも個人事業主として申請可。会計・請求・顧客管理・生成AI搭載SaaSが本命。カメラ本体は対象外。",
        "amt": "補助率1/2（条件で2/3）。1〜3プロセス：5〜150万円／4プロセス以上：150〜450万円",
        "who": "中小・小規模。映像制作の個人事業主は対象になりやすい。",
        "fit": [
            "□ 開業届を出している個人事業主（または法人）",
            "□ 従業員300人以下の中小（サービス業）→ YES",
            "□ GビズIDプライムを持っている／取れる",
            "□ SECURITY ACTION ★1つ星以上を宣言できる",
            "□ IT導入支援事業者が登録したツールを買う（自作ソフト・非登録のBlackmagicは不可）",
            "□ 労働生産性向上の数値目標を書ける",
        ],
        "guide": "登録済みITツール（会計freee、請求、CRM、生成AI業務ツール等）の導入費・クラウド2年分が対象。撮影カメラ・レンズ・ドローン単体は対象外。UA運営の経理・案件管理・AI文字起こし／リサーチ補助ならハマる。交付決定前の発注は全額自己負担になる。",
        "inputs": "GビズID／SECURITY ACTION宣言ID／業種・従業員数・資本金／直近売上／導入ツール名（支援事業者が入力）／労働生産性の現状値と3年後目標／賃金引き上げ方針",
        "docs": "履歴事項全部証明書または開業届／直近の確定申告書B＋青色決算書／労働者名簿（いなければ従業員0と明記）／SECURITY ACTION宣言画面／見積は支援事業者が用意",
        "link": "https://it-shien.smrj.go.jp/applicant/subsidy/normal/",
        "when": "直近：4次締切 2026/8/25 17:00（交付決定10/7予定）。5次9/29、6次10/30。支援事業者探しが先。交付決定前に買わない。",
        "deadline": "4次 8/25",
    },
    {
        "no": 2,
        "cat": "AI / IT",
        "name": "デジタル化・AI導入補助金2026　セキュリティ対策推進枠",
        "pct": 44,
        "why": "通常枠と同じ土台。EDR・UTM等の登録セキュリティ製品なら通る。映像会社の顧客データ保護として説明可能。",
        "amt": "5〜150万円。補助率1/2（小規模は2/3）",
        "who": "中小・小規模。SECURITY ACTION必須。",
        "fit": [
            "□ 個人事業主または法人",
            "□ SECURITY ACTION宣言済",
            "□ 登録セキュリティITツールを導入する",
            "□ カメラや編集ソフトのセキュリティではない（製品カテゴリがセキュリティであること）",
        ],
        "guide": "IPA「サイバーセキュリティお助け隊」掲載かつ事務局登録サービスのみ。Amazonで買う市販ソフトは不可。IT導入支援事業者経由。通常枠と同時申請は不可。",
        "inputs": "通常枠とほぼ同じ＋導入するセキュリティ機能の説明／情報資産の種類（顧客映像・個人情報）",
        "docs": "確定申告／開業届または登記／SECURITY ACTION／支援事業者との事業計画",
        "link": "https://it-shien.smrj.go.jp/applicant/subsidy/security/",
        "when": "通常枠と同じ締切。4次 2026/8/25 17:00。5次9/29、6次10/30。枠を間違えない。",
        "deadline": "4次 8/25",
    },
    {
        "no": 3,
        "cat": "AI / IT",
        "name": "デジタル化・AI導入補助金2026　インボイス枠",
        "pct": 40,
        "why": "適格請求書発行事業者なら会計・請求ソフトが通りやすい。PCは上限10万円と薄い。",
        "amt": "1機能：〜50万円／2機能以上：〜350万円。小規模は50万以下4/5・超えた分2/3。PC等ハードはソフトとセットのみ（単体不可）",
        "who": "インボイス発行事業者の中小。",
        "fit": [
            "□ 適格請求書発行事業者番号を持っている",
            "□ 会計・受発注・決済ソフトを導入／乗り換えたい",
            "□ 登録ツールである（ハードウェア単体は不可）",
        ],
        "guide": "インボイス対応の会計・受発注・決済が主戦場。撮影機材の足しにはならない。経理のデジタル化として使う。",
        "inputs": "登録番号（T+13桁）／導入ソフト／請求業務の現状（手入力・Excel等）",
        "docs": "確定申告／開業届／インボイス登録通知／SECURITY ACTION／GビズID",
        "link": "https://it-shien.smrj.go.jp/applicant/subsidy/digitalbase",
        "when": "通常枠と同じ。4次 2026/8/25 17:00。5次9/29、6次10/30。",
        "deadline": "4次 8/25",
    },
    {
        "no": 4,
        "cat": "撮影 / 設備",
        "name": "中小企業省力化投資補助金（カタログ注文型）",
        "pct": 18,
        "why": "人手不足解消の汎用設備カタログ。シネマカメラはまず載っていない。照明ロボット等が載っていれば例外。",
        "amt": "従業員規模で上限200〜1,000万円目安（賃上げ達成で上振れ）。補助率1/2",
        "who": "人手不足の中小。カタログ掲載製品のみ。",
        "fit": [
            "□ 従業員がいる／これから雇う（一人親方は弱い）",
            "□ カタログに欲しい機材がある（要検索）",
            "□ 賃上げ計画を出せる",
        ],
        "guide": "登録製品を選んで買う方式。BMDカメラ・ジンバル・ドローンは対象外になりやすい。編集スタジオの自動化設備があれば見る。第8回は2026年8月中旬開始予定。",
        "inputs": "製品型番（カタログID）／導入台数／労働時間削減見込み／賃上げ計画",
        "docs": "GビズID／決算書／労働者名簿／賃金台帳／カタログ製品の見積",
        "link": "https://shoryokuka.smrj.go.jp/",
        "when": "公募回制。カタログ検索が先。第8回は2026年8月中旬開始予定だったので公式で開いているか確認。",
        "deadline": "回次確認",
    },
    {
        "no": 5,
        "cat": "AI / 撮影システム",
        "name": "中小企業省力化投資補助金（一般型）オーダーメイド",
        "pct": 14,
        "why": "自社向けに組む省力化システム（AI文字起こし＋素材管理＋自動書き出し等）なら理論上可。申請が重く、従業員・賃上げ前提。",
        "amt": "従業員規模で上限750万〜8,000万（特例で最大1億）。中小1/2、小規模2/3",
        "who": "人手不足の中小。個別開発の設備・システム。",
        "fit": [
            "□ 外注ではなく「社内の繰り返し作業」を機械化する話になっている",
            "□ 従業員がいる（今は0なので弱い）",
            "□ 3〜5年の事業計画・賃金計画を書ける",
            "□ ベンダーと要件定義できる",
        ],
        "guide": "AC/ME量産の自動編集ライン、素材アーカイブAIなど「オーダーメイド」にする必要がある。市販SaaSだけならAI導入補助金の方が正しい。今は時期尚早。法人＋1人雇用後。",
        "inputs": "現状の工数／削減時間／導入システムの仕様／賃上げ目標／付加価値額",
        "docs": "事業計画書（指定様式）／決算2期／労働者名簿／見積・仕様書／GビズID",
        "link": "https://shoryokuka.smrj.go.jp/ippan/",
        "when": "公募回制。第8回は2026年8月中旬予定。公式で開閉を確認。",
        "deadline": "回次確認",
    },
    {
        "no": 6,
        "cat": "販路 / UA",
        "name": "小規模事業者持続化補助金（一般型）",
        "pct": 50,
        "why": "従業員5人以下のサービス業に該当。UAの広告・HP・展示・チラシが本命。映画制作費には使えない。",
        "amt": "通常枠上限50万円・補助率2/3。特例組合せで最大250万円程度の年もある",
        "who": "小規模事業者（商業・サービス：常時従業員5人以下）。個人事業主可。",
        "fit": [
            "□ 常時雇用5人以下 → YES",
            "□ 商工会議所または商工会の会員／相談ができる（東京なら所属地区）",
            "□ 販路開拓の計画（UAメンバーシップ、企業向け媒体キット、展示）",
            "□ 映画の撮影費・キャスト費ではない",
        ],
        "guide": "広報費・ウェブサイト・展示会が通りやすい。第20回は広報費・ウェブ費それぞれ税込30万上限で単独申請不可。東京23区は商工会議所地区。事業支援計画書（様式4）が必須。",
        "inputs": "経営計画（現状・強み・方針）／補助事業計画（何を売るか）／経費内訳／売上目標",
        "docs": "GビズIDプライム／確定申告／開業届／事業支援計画書・様式4（商工会議所が発行）／見積／賃金台帳（特例時）",
        "link": "https://r6.jizokukahojokin.info/",
        "when": "第20回：受付2026/11/5〜12/15 17:00。様式4発行は12/4締切。10月には会議所へ相談。",
        "deadline": "12/15（様式4は12/4）",
    },
    {
        "no": 7,
        "cat": "AI / 都",
        "name": "東京都 DX推進トータルサポート（AI活用／DX推進コース）",
        "pct": 28,
        "why": "都内中小の本命級。ただし先に公社アドバイザー支援の採択が必要。枠が少なく賃上げ計画が重い。",
        "amt": "AI活用コース上限2,000万（大幅賃上げで3,000万）、補助率2/3〜。DX推進コース上限3,000万",
        "who": "都内に主たる事業所の中小・個人事業主。アドバイザー支援を受けた者のみ助成申請可。",
        "fit": [
            "□ 都内事業所 → YES",
            "□ アドバイザー派遣コースに採択される（倍率高い）",
            "□ 賃上げ計画を従業員に対して書ける（今は従業員0で弱い）",
            "□ AI活用の業務課題が具体（文字起こし、素材検索、案件管理など）",
        ],
        "guide": "「先に相談・伴走、その提案書で機械を買う」型。R8の4〜5月募集は終了。生産性向上コースは年2回想定。一人事業はAI活用のストーリーが弱いので、法人＋外注を内部化したあとの方が良い。",
        "inputs": "経営課題／AIで消す作業／導入システム／賃上げ率／従業員数",
        "docs": "アドバイザー提案書／決算／登記または開業届／見積・仕様／賃上げ計画",
        "link": "https://iot-robot.jp/business/dxtotalsupportsubsidy/",
        "when": "R8一次は終了。次回募集をポータルで追う。アドバイザー支援の採択が先。",
        "deadline": "次回待ち",
    },
    {
        "no": 8,
        "cat": "IT / 都",
        "name": "東京都 サイバーセキュリティ対策促進助成金",
        "pct": 32,
        "why": "都内中小でUTM・EDR等。下限10万。個人でも可だが法人の方が書類が揃いやすい。二つ星必須。",
        "amt": "上限500万円・下限10万円・助成率1/2",
        "who": "都内中小。SECURITY ACTION ★★二つ星宣言済み。",
        "fit": [
            "□ 都内で事業 → YES",
            "□ ★★二つ星を宣言できる（一つ星では足りない）",
            "□ セキュリティ機器・クラウドを新規導入する（下限10万以上の経費）",
            "□ 撮影機材の盗難保険ではない",
        ],
        "guide": "R8第2回：2026年9月9日〜9月15日。Jグランツ申請。情報セキュリティ基本方針の作成が必要。",
        "inputs": "導入機器の機種／設置場所／SECURITY ACTION ID／事業概要",
        "docs": "申請書Excel／反社誓約／確定申告1期／登記（法人）または開業関係／都税の納税証明／見積／仕様・カタログ／会社案内／SECURITY ACTION／情報セキュリティ基本方針／設置図面／工程表",
        "link": "https://www.cybersecurity.metro.tokyo.lg.jp/torikumi/741/index.html",
        "when": "第2回 2026/9/9 9:00〜9/15 17:00（Jグランツ）。第3回は2027/1/8〜1/15。期間が短いので書類を先に作れ。",
        "deadline": "9/9–9/15",
    },
    {
        "no": 9,
        "cat": "創業 / 都",
        "name": "東京都 創業助成事業（公社）",
        "pct": 8,
        "why": "上限400万は魅力だが、個人事業主としての経営通算5年未満が条件。フリー6年目なら原則アウト。",
        "amt": "上限400万・下限100万・助成率2/3。期間は交付決定から最長2年",
        "who": "都内創業予定 or 創業5年未満。かつ創業ステーション等の指定支援を修了していること。",
        "fit": [
            "□ 個人事業主期間が通算5年未満か？ → 6年目なら NO",
            "□ 法人化しても「別事業含む通算」で見られる → リセットされない",
            "□ TOKYO創業ステーション等の支援修了",
            "□ GビズIDプライム",
        ],
        "guide": "対象経費は賃料・広告・備品・専門家・従業員人件費等。映画制作費そのものではない。第2回申請：2026/9/29〜10/8。通算年数を開業届で確認してから動くこと。",
        "inputs": "創業日／支援事業の修了番号／資金計画／売上計画",
        "docs": "事業計画書／開業届または登記／確定申告／創業支援修了証明／見積／GビズID",
        "link": "https://startup-station.jp/m2/services/sogyokassei/",
        "when": "第2回 2026/9/29-10/8。開業届の開業日が通算5年を超えていたら出さない。",
        "deadline": "9/29–10/8",
    },
    {
        "no": 10,
        "cat": "事業 / 全国",
        "name": "新事業進出補助金（ものづくり商業サービス系の後継枠）",
        "pct": 16,
        "why": "UAのIP・新サービスを「新市場」として組めるが、革新性と賃上げの審査が重い。撮影費の穴埋めには不向き。",
        "amt": "枠により数百万円〜数千万円。補助率1/2前後（要最新要領）",
        "who": "中小の新事業・新製品・新サービス。",
        "fit": [
            "□ 既存の受託映像とは明確に違う新事業か（UAメンバーシップ／IP）",
            "□ 3〜5年計画と賃上げを書ける",
            "□ 認定支援機関の確認が必要になることが多い",
        ],
        "guide": "名称は年度で変わる（ものづくり補助金／新事業進出）。設備・システム開発が中心。NUR制作費には使えない。法人後にUAの事業計画が固まってから。",
        "inputs": "新事業の市場／競合／付加価値額／設備投資額／賃上げ",
        "docs": "事業計画（指定）／決算2期／認定支援機関の確認書／見積／労働者名簿",
        "link": "https://portal.monodukuri-hojo.jp/",
        "when": "公募回制。最新回の要領で名称を確認。",
        "deadline": "回次確認",
    },
    {
        "no": 11,
        "cat": "撮影 / 短編",
        "name": "ぐんま次世代映像クリエイターコンペ 2026",
        "pct": 38,
        "why": "NUR（赤城・覚満淵）と主題が一致。制作費100万＋県のロケ支援。今期締切済。来期が本命。",
        "amt": "企画通過9組に制作費100万円（税込）。大賞さらに100万円",
        "who": "ディレクター個人。商業映画の監督経験がないこと。群馬を撮影地または舞台にした短編。",
        "fit": [
            "□ 商業映画の監督経験なし → おそらく YES",
            "□ 群馬で撮る／群馬が舞台 → NURは YES",
            "□ R15+/成人向けではない",
            "□ 他の制作支援に同じ企画で採択されていない",
            "□ 2027年1月末完成に合わせられる",
        ],
        "guide": "一次は企画シート。通過後に制作。完成作品の県PR利用許諾あり。著作権は制作者。2026応募は7/26終了。",
        "inputs": "企画概要／ロケ地／スケジュール／予算（100万内訳）／監督プロフィール",
        "docs": "映像企画シート（指定）／応募フォーム入力／面談（二次・三次）",
        "link": "https://gngfc2026.pref.gunma.jp/",
        "when": "2026応募は7/26終了。2027年度の同型を公式で待て。",
        "deadline": "今期終了",
    },
    {
        "no": 12,
        "cat": "撮影 / 群馬",
        "name": "ぐんまFC 映像作品制作等支援補助金",
        "pct": 11,
        "why": "下限500万・県内事業者への支払いが大きい。NURでは足りない。長編で群馬主ロケ＋県内発注を積めば検討。",
        "amt": "補助率1/2、下限500万〜上限2,000万（Gメッセ利用で最大2,200万）",
        "who": "群馬県内で映画・ドラマ・ドキュメンタリー等を制作し、県内事業者へ一定額を支払う商業作品。",
        "fit": [
            "□ 県内宿泊・食事・交通・施設を県内事業者に支払う",
            "□ 補助対象経費が下限に届く規模か → NURは NO",
            "□ 交付決定から5年以内公開の商業作品",
            "□ 交付決定希望日の数週間前までに申請",
        ],
        "guide": "ロケ協力（ぐんまFC／前橋FC）自体は無料相談可。補助金は大型作品向け。まずはFCにロケ相談、補助金はプールサイド級になってから。",
        "inputs": "県内支出内訳／公開予定／作品概要／スケジュール",
        "docs": "申請書／予算書／県内見積／企画書／公開計画",
        "link": "https://www.pref.gunma.jp/site/hojokin/643955.html",
        "when": "通年。大型化してから。ロケ相談は https://www.gunma-fc.jp/production/",
        "deadline": "通年",
    },
    {
        "no": 13,
        "cat": "映画 / 都",
        "name": "アーツカウンシル東京 創造発信助成 カテゴリーI（単年）",
        "pct": 34,
        "why": "都内在住個人で申請可。NURの都内上映・展示に50万。撮影費より発表費。",
        "amt": "個人：都内創造50万／国際交流50万。経費の1/2以内＋創作環境サポート最大10万",
        "who": "都内在住の個人芸術家、または都内本部の団体。",
        "fit": [
            "□ 東京都在住 → YES",
            "□ 主催する上映・展示が都内（または国際交流の定義を満たす）",
            "□ 公開活動である（撮影だけは弱い）",
            "□ 消費税は対象外",
        ],
        "guide": "「作る」より「東京で発表する」。NUR完成後のスクリーニング企画として組む。第2期は2026/8/4締切済。年2期（2月頃・6〜8月）。",
        "inputs": "事業趣旨／日程／会場／収支予算／キャリア段階／東京との関係",
        "docs": "オンライン申請一式／収支予算書／プロフィール／会場の確認書類／見積",
        "link": "https://www.artscouncil-tokyo.jp/grants/tokyo-grant-program/",
        "when": "第2期は2026/8/4締切済。次回は2027年度第1期（例年2月）。",
        "deadline": "次回2月頃",
    },
    {
        "no": 14,
        "cat": "映画 / 海外",
        "name": "アーツカウンシル東京 カテゴリーIV 海外映画祭参加（長期）",
        "pct": 30,
        "why": "個人で2年200万／3年300万。ポスプロ＋海外映画祭。NURの出口設計と一致。計画の具体性が勝負。",
        "amt": "個人：2年200万／3年300万、経費1/2以内。団体は倍額",
        "who": "都内在住の監督・P、または都内本部団体（核の監督／Pが都内在住）。",
        "fit": [
            "□ 都内在住監督 → YES",
            "□ 海外映画祭を目指すポスプロ計画がある",
            "□ 2〜3年事業として書ける",
            "□ 2026年度は7/30締切済",
        ],
        "guide": "撮影費ではなくグレーディング、字幕、DCP、渡航・宿泊。対象期間は2027年1月以降開始の回だった。来年度要領を読め。",
        "inputs": "目標映画祭リスト／ポスプロ工程／年度ごとの収支／スタッフ",
        "docs": "オンライン申請／複数年収支／作品概要／監督経歴／見積",
        "link": "https://www.artscouncil-tokyo.jp/grants/tokyo-grant-program/28215/",
        "when": "年1回・初夏が目安。2026年度は7/30締切済。",
        "deadline": "来年夏",
    },
    {
        "no": 15,
        "cat": "映画 / 国",
        "name": "文化庁／芸文振 日本映画製作支援 劇映画B（若手）",
        "pct": 17,
        "why": "長編専用。1時間以上・予算総額1,500万以上。法人必須。NURは対象外。プールサイド用。",
        "amt": "約535万円。若手監督加算で最大約824万。映適認定で上限+30%",
        "who": "映画製作を目的に定款へ書いた日本の法人。著作権の全部または一部を保有し、出資していること。",
        "fit": [
            "□ 法人がある → 今は NO（作ってから）",
            "□ 作品が1時間以上 → NURは NO、長編は YES",
            "□ 予算総額1,500万円以上",
            "□ 監督が若手・新進の定義に入る",
        ],
        "guide": "個人申請不可。完成形式はDCP等。労働ガイドラインの申告あり。募集は年2回（秋・春）。R8第2回は2026/5終了。",
        "inputs": "要望書Excel（総表・個表・収支・スタッフ／キャスト内訳）／脚本／団体概要",
        "docs": "定款／財務諸表／脚本製本／監督略歴／応募要件確認書／取引ガイドライン申告／組織自己申告／映適申請状況",
        "link": "https://www.ntj.jac.go.jp/grant/program/applicant/08/",
        "when": "次回目安 2026年10〜11月（翌年度第1回）。法人＋長編になってから。",
        "deadline": "秋目安",
    },
    {
        "no": 16,
        "cat": "映画 / 海外",
        "name": "UNIJAPAN 海外映画祭・芸術祭出品支援（文化庁委託）",
        "pct": 48,
        "why": "公式出品が決まったあとの字幕・渡航。決まれば採択は比較的高い。今は作品未完成なので条件付き。",
        "amt": "外国語字幕製作費・渡航費等（コードにより上限が異なる。要規約）",
        "who": "対象映画祭に出品する日本映画の製作者。自主映画はコードC。",
        "fit": [
            "□ 対象リストの映画祭・芸術祭に正式招待／出品",
            "□ 日本映画である",
            "□ 字幕または渡航の実費が発生する",
        ],
        "guide": "制作費ではない。三大映画祭は別コード。出品決定後すぐに申請。",
        "inputs": "映画祭名／部門／招待状／見積（字幕会社・航空券）",
        "docs": "申請書／招待または出品証明／作品情報／見積／領収は後で精算",
        "link": "https://www.unijapan.org/oversea/support/",
        "when": "出品決定の都度。令和8年度実施中。",
        "deadline": "出品後すぐ",
    },
    {
        "no": 17,
        "cat": "映像 / 国",
        "name": "文化庁 メディア芸術クリエイター育成（創作／発表）",
        "pct": 22,
        "why": "メディアアート・ゲーム・アニメ・マンガ寄り。NURの実写詩は外れやすい。3DCG実験として出すなら可能性。",
        "amt": "創作支援最大500万円／発表支援最大100万円（税込）",
        "who": "概ね40代まで。創作は活動5年または受賞歴。発表は活動3年。個人または団体。",
        "fit": [
            "□ 27歳・活動6年 → 年齢・年数は YES",
            "□ 企画がメディア芸術の定義に入るか（実写映画は弱い）",
            "□ 国の他助成と二重取りは不可",
        ],
        "guide": "R8は2026/6/2締切済。成果発表イベントあり。NURを無理にねじ込まない。CG／インスタレーション寄り別企画なら来年。",
        "inputs": "企画趣旨／予算／活動歴／同時応募中の助成",
        "docs": "指定エントリー／ポートフォリオ／予算書／経歴",
        "link": "https://creators.j-mediaarts.bunka.go.jp/2026-entry",
        "when": "例年春。R8は2026/6/2締切済。来年度を待て。",
        "deadline": "来年春",
    },
    {
        "no": 18,
        "cat": "映画祭",
        "name": "PFFアワード（ぴあフィルムフェスティバル）",
        "pct": 26,
        "why": "助成金ではなくコンペ。入選が visibility、スカラシップが次作資金。NURの出口として必須級。",
        "amt": "賞金・上映・海外展開支援。入選後のPFFスカラシップは別途（次作）",
        "who": "長さ・ジャンル・年齢・国籍不問の自主映画。",
        "fit": [
            "□ 完成作品がある（または完成予定が募集に間に合う）",
            "□ 自主制作である",
            "□ 他映画祭とのプレミア規定を確認できる",
        ],
        "guide": "2026応募は2/1〜3/17で終了。毎年冬〜春。NUR完成年度の回に出せ。",
        "inputs": "作品情報／監督情報／プレミア状況／スクリーナーURL",
        "docs": "応募フォーム／作品ファイル／スチル／台詞リスト（指定があれば）",
        "link": "https://pff.jp/jp/",
        "when": "次回は2027年2〜3月が目安。NUR完成年度の回に出せ。",
        "deadline": "来年2–3月",
    },
    {
        "no": 19,
        "cat": "雇用",
        "name": "キャリアアップ助成金（正社員化コース）",
        "pct": 6,
        "why": "今は従業員ゼロで対象外。編集・PMを有期で雇い、正社員化したあと。",
        "amt": "中小：有期→正規 1人あたり40万円（重点支援対象は80万円）",
        "who": "雇用保険適用事業主。対象は雇っている非正規。事業主本人は対象外。",
        "fit": [
            "□ 雇用保険の適用事業所か → 今は NO",
            "□ 有期で6ヶ月以上雇った人を正社員にする計画",
            "□ 就業規則に転換制度を書く",
            "□ 転換前にキャリアアップ計画を労働局へ提出済み",
        ],
        "guide": "後出しは不可。雇う前に計画届。フリーの外注契約を雇用に切り替えるときだけ意味がある。",
        "inputs": "転換対象者／雇用期間／賃金／就業規則の転換条項",
        "docs": "キャリアアップ計画届／就業規則／雇用契約／賃金台帳／出勤簿／雇用保険関係",
        "link": "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/part_haken/jigyounushi/career.html",
        "when": "通年。雇う決定の1ヶ月以上前に計画。",
        "deadline": "雇用後",
    },
    {
        "no": 20,
        "cat": "雇用 / 研修",
        "name": "人材開発支援助成金（人材育成／リスキリング）",
        "pct": 7,
        "why": "従業員の研修費。自分のスキルアップには使えない。雇ってからPremiere／AI研修を受けさせる用。",
        "amt": "経費助成 中小最大60〜75%＋賃金助成（コースによる）",
        "who": "雇用保険適用事業主。対象は被保険者である従業員。",
        "fit": [
            "□ 従業員が雇用保険に入っている → 今は NO",
            "□ 訓練開始1ヶ月前に計画届",
            "□ 事業主本人の講座は対象外",
        ],
        "guide": "リスキリングコースはR8年度末までの時限あり。編集スタッフを雇った年に使う。",
        "inputs": "訓練カリキュラム／時間／対象者／OFF-JT機関",
        "docs": "訓練計画届／実施報告書／領収／賃金台帳／雇用契約",
        "link": "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_nenkin/koyou/kyufukin/d01-1.html",
        "when": "通年。計画届が先。",
        "deadline": "雇用後",
    },
]


def draw_cover(c, total_pages):
    header(c, 1, total_pages, "COVER")
    c.bookmarkPage("cover")
    c.setFont(FONT, 22)
    c.setFillColor(MUTED)
    c.drawString(56, 960, "PERSONAL USE  /  NOT LEGAL ADVICE")
    c.setFont(FONT, 54)
    c.setFillColor(INK)
    c.drawString(56, 880, "受けられそうな助成・補助金")
    c.setFont(FONT, 28)
    c.drawString(56, 830, "映画・撮影 ＋ AI・ITツール  国内20件")
    c.setFont(FONT, 18)
    c.setFillColor(MUTED)
    lines = [
        "対象者想定：1998年生まれ／東京在住／映像ディレクター／フリー6年目／就職経験なし",
        "個人事業（法人化検討）／従業員なし／UA運営／NUR短編→長編『プールサイド』",
        "判定日：2026-08-17。公募は毎年変わる。申請前に必ず公式要領を当たること。",
        "％は「今のスペックのまま出して通る現実味」（制度適合×競争×準備負荷）。保証ではない。",
    ]
    y = 740
    for t in lines:
        c.drawString(56, y, t)
        y -= 32
    c.setFillColor(RED)
    c.setFont(FONT, 18)
    c.drawString(56, 390, "直近で動ける締切（2026-08-17時点）")
    c.setFont(FONT, 16)
    c.setFillColor(INK)
    c.drawString(56, 355, "8/25 17:00　デジタル化・AI導入 4次（通常／セキュリティ／インボイス）← 今週")
    c.drawString(56, 325, "9/9–9/15　　東京都サイバーセキュリティ対策促進 第2回")
    c.drawString(56, 295, "11/5–12/15　持続化補助金 第20回（様式4は12/4）")

    c.setFillColor(INK)
    c.rect(56, 430, 600, 210, fill=0, stroke=1)
    c.setFont(FONT, 16)
    c.drawString(76, 610, "このPDFの使い方")
    c.setFont(FONT, 15)
    c.setFillColor(MUTED)
    draw_wrap(
        c,
        "各制度ページのチェック□を自分で埋める。全部YESなら申請検討。赤字は書類・作成物。入力項目は電子申請で聞かれる中身。青いURLはクリックで公式へ。",
        76,
        575,
        15,
        540,
        MUTED,
    )
    c.setFillColor(RED)
    c.setFont(FONT, 16)
    c.drawString(76, 455, "赤字＝書類作成・添付が必要なもの")
    c.setFillColor(INK)
    c.rect(680, 430, 1180, 210, fill=0, stroke=1)
    c.setFont(FONT, 16)
    c.drawString(700, 610, "今やってはいけないこと")
    c.setFont(FONT, 15)
    c.setFillColor(MUTED)
    draw_wrap(
        c,
        "交付決定前に機材を買う。創業5年未満助成を法人化でリセットできると思う。NUR短編を文化庁・劇映画Bに出す。カメラ本体をIT導入補助金で買おうとする。従業員ゼロで雇用助成を申請する。",
        700,
        575,
        15,
        1130,
        MUTED,
    )


def draw_howto(c, total_pages):
    header(c, 2, total_pages, "HOW TO READ")
    c.setFont(FONT, 36)
    c.setFillColor(INK)
    c.drawString(56, 980, "読み方 ／ 共通で先に作るもの")
    items = [
        ("GビズIDプライム", "IT・持続化・都の電子申請の鍵。印鑑証明が要る。取得に2〜3週間。今すぐ https://gbiz-id.go.jp/"),
        ("SECURITY ACTION", "IT導入・都セキュリティの前提。IPAサイトで自己宣言。★と★★を取り違えない。"),
        ("確定申告一式", "直近1〜2期。青色決算書まで。黒塗りして出す制度あり。"),
        ("開業届 or 登記", "個人の証明。法人化後は履歴事項全部証明書（3ヶ月以内）。"),
        ("見積（税抜）", "交付決定前発注はほぼ全滅。見積日付と社名を揃えろ。"),
    ]
    y = 900
    for title, body in items:
        c.setFillColor(RED)
        c.setFont(FONT, 18)
        c.drawString(56, y, "■ " + title)
        c.setFillColor(MUTED)
        c.setFont(FONT, 16)
        draw_wrap(c, body, 80, y - 28, 16, 1780, MUTED)
        y -= 100
    c.setFillColor(INK)
    c.setFont(FONT, 18)
    c.drawString(56, 360, "％の目安")
    c.setFont(FONT, 16)
    c.setFillColor(MUTED)
    draw_wrap(
        c,
        "45%以上＝今の延長で狙える。25〜44%＝条件を足せば現実的。24%以下＝今は時間対効果が悪い（法人化・雇用・長編化のあと）。コンペは中身勝負なので％は「出せる状態か」寄り。",
        56,
        320,
        16,
        1800,
        MUTED,
    )


def draw_index(c, total_pages):
    header(c, 3, total_pages, "INDEX")
    c.setFont(FONT, 36)
    c.setFillColor(INK)
    c.drawString(56, 980, "20件一覧 ／ 今の採択現実味")
    c.setFont(FONT, 13)
    c.setFillColor(MUTED)
    c.drawString(56, 940, "No")
    c.drawString(110, 940, "分野")
    c.drawString(260, 940, "制度")
    c.drawString(1480, 940, "直近締切")
    c.drawRightString(1860, 940, "%")
    c.setStrokeColor(LINE)
    c.line(56, 928, 1864, 928)
    y = 900
    for g in GRANTS:
        c.linkRect("", f"g{g['no']}", (56, y - 10, 1864, y + 22), relative=0)
        c.setFillColor(pct_color(g["pct"]))
        c.setFont(FONT, 18)
        c.drawRightString(1860, y, f"{g['pct']}%")
        c.setFillColor(INK)
        c.setFont(FONT, 16)
        c.drawString(56, y, f"{g['no']:02d}")
        c.setFillColor(MUTED)
        c.drawString(110, y, g["cat"])
        c.setFillColor(INK)
        name = g["name"]
        if sw(name, 16) > 1180:
            while sw(name + "…", 16) > 1180:
                name = name[:-1]
            name += "…"
        c.drawString(260, y, name)
        c.setFillColor(MUTED)
        c.setFont(FONT, 14)
        c.drawString(1480, y, g.get("deadline", ""))
        y -= 40


def draw_grant(c, g, page, total_pages):
    header(c, page, total_pages, f"#{g['no']:02d}  {g['cat']}")
    c.bookmarkPage(f"g{g['no']}")
    c.setFillColor(pct_color(g["pct"]))
    c.roundRect(56, 955, 160, 48, 6, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont(FONT, 22)
    c.drawCentredString(136, 970, f"{g['pct']}%")
    c.setFillColor(INK)
    c.setFont(FONT, 28)
    title = g["name"]
    draw_wrap(c, title, 236, 988, 26, 1620, INK, leading=32, max_lines=2)

    draw_wrap(c, "今の自分での現実味：" + g["why"], 56, 928, 14, 1808, MUTED, leading=20, max_lines=2)

    # left column
    x1, w1 = 56, 900
    y = 880
    c.setFillColor(INK)
    c.setFont(FONT, 16)
    c.drawString(x1, y, "金額・条件")
    y -= 8
    c.setStrokeColor(LINE)
    c.line(x1, y, x1 + w1, y)
    y -= 28
    y -= draw_wrap(c, g["amt"], x1, y, 15, w1, INK, leading=22)
    y -= 10
    y -= draw_wrap(c, "対象：" + g["who"], x1, y, 15, w1, MUTED, leading=22)
    y -= 18
    c.setFillColor(INK)
    c.setFont(FONT, 16)
    c.drawString(x1, y, "自分が当てはまるか（全部YESなら申請検討）")
    y -= 8
    c.line(x1, y, x1 + w1, y)
    y -= 30
    for line in g["fit"]:
        y -= draw_wrap(c, line, x1, y, 16, w1, INK, leading=24)
        y -= 6

    y -= 10
    c.setFillColor(INK)
    c.setFont(FONT, 16)
    c.drawString(x1, y, "募集要項（超要約）")
    y -= 8
    c.line(x1, y, x1 + w1, y)
    y -= 28
    draw_wrap(c, g["guide"], x1, y, 15, w1, MUTED, leading=22, max_lines=8)

    # right
    x2, w2 = 1000, 864
    y = 880
    c.setFillColor(INK)
    c.setFont(FONT, 16)
    c.drawString(x2, y, "入力項目（電子申請で聞かれる中身）")
    y -= 8
    c.setStrokeColor(LINE)
    c.line(x2, y, x2 + w2, y)
    y -= 28
    y -= draw_wrap(c, g["inputs"], x2, y, 15, w2, INK, leading=22)
    y -= 20
    c.setFillColor(RED)
    c.setFont(FONT, 16)
    c.drawString(x2, y, "必要書類・作成物（赤字）")
    y -= 8
    c.setStrokeColor(RED)
    c.line(x2, y, x2 + w2, y)
    y -= 28
    y -= draw_wrap(c, g["docs"], x2, y, 15, w2, RED, leading=22)
    y -= 20
    c.setStrokeColor(LINE)
    c.setFillColor(INK)
    c.setFont(FONT, 16)
    c.drawString(x2, y, "時期")
    y -= 8
    c.line(x2, y, x2 + w2, y)
    y -= 28
    y -= draw_wrap(c, g["when"], x2, y, 15, w2, MUTED, leading=22)
    y -= 16
    c.setFillColor(INK)
    c.setFont(FONT, 16)
    c.drawString(x2, y, "公式リンク")
    y -= 26
    c.setFillColor(HexColor("#0B57D0"))
    c.setFont(FONT, 14)
    link_h = draw_wrap(c, g["link"], x2, y, 14, w2, HexColor("#0B57D0"), leading=20)
    c.linkURL(g["link"], (x2, y - link_h + 4, x2 + min(w2, sw(g["link"], 14) + 8), y + 16), relative=0)


def draw_plan(c, total_pages):
    header(c, total_pages, total_pages, "ACTION")
    c.setFont(FONT, 36)
    c.setFillColor(INK)
    c.drawString(56, 980, "今からやる順番（映画を食わない範囲）")
    steps = [
        "今週：GビズIDプライム申請。開業日を開業届で確認（創業助成を殺すかどうかが決まる）。",
        "IT：デジタル化・AI導入は「会計＋案件管理＋生成AI」で組め。カメラは自分の金。IT導入支援事業者を先に探す。",
        "UA：持続化補助金の次回に広告・HP・展示。商工会議所へ先に顔を出す。",
        "セキュリティ：二つ星宣言。都の9月公募かIT導入のセキュリティ枠、どちらか一方。",
        "NUR：群馬コンペの来期＋完成後にアーツカウンシルとPFF。UNIJAPANは出品が決まってから。",
        "長編：法人化してから文化庁・劇映画B。今の時間を申請書に溶かすな。",
        "雇用助成：人を雇うと決めた月に労働局へ計画届。後付けは死ぬ。",
        "同一経費の二重取りは不可。映画の助成とITの助成は経費を分ける。",
    ]
    y = 900
    for i, s in enumerate(steps, 1):
        c.setFillColor(INK)
        c.setFont(FONT, 18)
        c.drawString(56, y, f"{i}.")
        draw_wrap(c, s, 100, y, 18, 1760, INK, leading=26)
        y -= 70
    c.setFillColor(HexColor("#0B57D0"))
    c.setFont(FONT, 14)
    c.drawString(56, 310, "GビズID  https://gbiz-id.go.jp/")
    c.linkURL("https://gbiz-id.go.jp/", (56, 300, 520, 328), relative=0)
    c.setFillColor(RED)
    c.setFont(FONT, 16)
    c.drawString(56, 270, "注意：このPDFの％・要件は公募要領の要約。最新PDFを公式からダウンロードしてから申請すること。")


def main():
    total = 3 + len(GRANTS) + 1
    out_paths = [
        Path("/home/ubuntu/Desktop/助成金チェックリスト_UNGR_2026.pdf"),
        Path("/workspace/artifacts/助成金チェックリスト_UNGR_2026.pdf"),
        Path("/workspace/助成金チェックリスト_UNGR_2026.pdf"),
    ]
    Path("/home/ubuntu/Desktop").mkdir(parents=True, exist_ok=True)
    Path("/workspace/artifacts").mkdir(parents=True, exist_ok=True)

    dest = out_paths[0]
    c = canvas.Canvas(str(dest), pagesize=(W, H))
    c.setTitle("助成金チェックリスト UNGR 2026")
    c.setAuthor("UNGR ARCHIVE")

    draw_cover(c, total)
    c.showPage()
    draw_howto(c, total)
    c.showPage()
    draw_index(c, total)
    c.showPage()
    for i, g in enumerate(GRANTS):
        draw_grant(c, g, 4 + i, total)
        c.showPage()
    draw_plan(c, total)
    c.save()

    data = dest.read_bytes()
    for p in out_paths[1:]:
        p.write_bytes(data)
    print("wrote", dest, dest.stat().st_size)
    for p in out_paths:
        print(p, p.exists(), p.stat().st_size if p.exists() else 0)


if __name__ == "__main__":
    main()
