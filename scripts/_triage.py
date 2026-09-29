#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_triage.py — 一轮人工目检结论落盘（SPEC §3.1/§5.2）。

对 data/provenance.csv 现有候选应用人工判定：
  - decision → train / reject（含 family / theme_primary / decision_reason）
  - train 的 Commons 古画补 creator / publication_year（PD-Art，时间证据进字段，gate 可过）
  - reject 的目录从 inbox/raw 移到 data/rejected/（连同理由留在 csv，§5）
  - 清理空目录与目检缩略图
幂等：重复运行结果一致。
"""

import csv
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/provenance.csv"
RAW = ROOT / "data/inbox/raw"
REJ = ROOT / "data/rejected"

FIELDS = ["file_id", "orig_filename", "train_filename", "source", "institution", "page_url",
          "direct_url", "license", "license_url", "creator", "creator_death_year",
          "publication_year", "family", "theme_primary", "width", "height", "sha256",
          "decision", "decision_reason", "downloaded_at"]

# file_id -> dict；reason 为人工结论（中文，引 SPEC 节号）
T = {
    # ---------- train ----------
    "commons_Clarke_The_Two_Distilleries_on_the_Same_Hill_1925_png": dict(
        decision="train", family="G", theme_primary="nature",
        reason="人工目检可留：Harry Clarke(卒1931) 1925 插图 PD，3840x5299 大图；线描+平涂装饰，G 族；theme 暂定 nature，以 caption 为准。"),
    "commons_Ivan_Bilibin_111_gif": dict(
        decision="review", family="C", theme_primary="court", train_filename="",
        reason="风格可留（Bilibin 卒1942 俄童话插图 PD，C 族）；但短边638<640，Commons 亦无更大版本，按 §5.2 移出训练集（三件套暂存 data/crops/_hold，换到高清源再入册）。"),
    "commons_Ivan_Bilibin_112_gif": dict(
        decision="review", family="C", theme_primary="court", train_filename="",
        reason="风格可留（Bilibin 1904 插图 PD，C 族）；但短边621<640，无更大版本，按 §5.2 移出训练集（暂存 data/crops/_hold）。"),
    "commons_Ivan_Bilibin_789_jpg": dict(
        decision="review", family="C", theme_primary="nature", train_filename="",
        reason="风格可留（Bilibin 1903 插图 PD，C 族）；但短边564<640，无更大版本，按 §5.2 移出训练集（暂存 data/crops/_hold）。"),
    "commons_Mogao_Cave_288_Devatas_at_the_Balcony_Western_Wei_period_jpg": dict(
        decision="train", family="A", theme_primary="ritual",
        creator="unknown artist, Western Wei mural (photo of PD 2D artwork, PD-Art)",
        publication_year="550",
        reason="人工目检可留：西魏(ca.550)莫高窟288窟天宫伎乐；石绿/石青/赭红矿物色平涂，A 族 ritual；2309x1195 可裁切。"),
    "commons_TsangMonk_jpg": dict(
        decision="train", family="A", theme_primary="ritual",
        creator="unknown artist, Dunhuang-school painting (PD on Commons)",
        publication_year="1000",
        reason="人工目检可留：敦煌系古画(观音坐像+云气，约10世纪) PD；775x949 达标；斑驳中等但纹样可读，可裁局部；A 族 ritual。原页年代待 Commons 限流解除后复核。"),
    "met_448280": dict(
        decision="train", family="B", theme_primary="court",
        reason="人工目检可留：Shahnama 1341 波斯细密画(Met CC0)；朱砂红地平涂+金，B 族 court；裁上方画幅带用。"),
    "met_451725": dict(
        decision="train", family="B", theme_primary="nature",
        reason="人工目检可留：Mantiq al-Tayr《The Concourse of the Birds》ca.1600(Met CC0)；B 族 nature(群鸟)。"),

    # ---------- train：2026-09-16 第三轮（补 court/ornament/nature；water 仍缺）----------
    "met_451289": dict(
        decision="train", family="F", theme_primary="ornament",
        reason="人工目检可留：Shah Jahan Album 泥金「unwan」首叶(ca.1630–40, Met CC0)，蓝地金花满铺、无人物情节，F 族纯图案；整页即图案，可直接裁去纸边。"),
    "met_451726": dict(
        decision="train", family="B", theme_primary="court",
        reason="人工目检可留：Mantiq al-Tayr《Shaikh San'an 于少女窗下》ca.1600(Met CC0)；蓝釉拱门+庭院人物+花树，B 族 court；裁去洒金绿边。"),
    "met_451403": dict(
        decision="train", family="B", theme_primary="court",
        reason="人工目检可留：《Wine Drinking in a Spring Garden》波斯单页(Met CC0)；青蓝/石绿袍服+花树+金，平涂闭合轮廓，B 族 court。"),
    "met_452651": dict(
        decision="train", family="B", theme_primary="nature",
        reason="人工目检可留：Shahnama《Isfandiyar 第三关·屠龙》页(Met CC0)；龙盘旋于赭红地+山石，B 族 nature；画幅在下三分之一，须裁画幅带。"),
    "commons_Zal_and_the_Simurgh_ink_and_opaque_watercolor_painting_from": dict(
        decision="train", family="B", theme_primary="nature",
        creator="unknown artist, Shahnama manuscript (PD on Commons)",
        publication_year="1500",
        reason="人工目检可留：Shahnama《Zal 与神鸟 Simurgh》细密画(Commons PD，Honolulu Academy of Arts 藏)；神鸟+密纹花树+粉山，平涂矿物色，B 族 nature；年代取文件页「late 15th or early 16th century」=1500；已裁中间画幅带。"),

    # ---------- reject：尺寸（§5.2 短边<640）----------
    "commons_A_late_T_ang_dynasty_Buddhist_donatress_jpg": dict(decision="reject", reason="拒：短边333<640（§5.2 尺寸门）。"),
    "commons_Bakst_Uzhin_jpg": dict(decision="reject", reason="拒：短边450<640（§5.2）。"),
    "commons_Clarke_Gone_is_the_ancient_alchemist_1925_png": dict(decision="reject", reason="拒：短边408<640（§5.2）。"),
    "commons_Dunhuang_Cave_220_Pipa_jpg": dict(decision="reject", reason="拒：短边443<640（§5.2）。"),
    "commons_Dunhuang_Cave_220_zheng_jpg": dict(decision="reject", reason="拒：短边439<640（§5.2）。"),
    "commons_Dunhuang_Cave_225_Konghou_jpg": dict(decision="reject", reason="拒：短边474<640（§5.2）。"),
    "commons_Dunhuang_Cave_299_Qin_jpg": dict(decision="reject", reason="拒：短边405<640（§5.2）。"),
    "commons_Dunhuang_Cave_428_Pipa_jpg": dict(decision="reject", reason="拒：短边376<640（§5.2）。"),
    "commons_Dunhuang_fresco_jpg": dict(decision="reject", reason="拒：短边567<640（§5.2）。"),
    "commons_Dunhuang_Zhang_Yichao_army_jpg": dict(decision="reject", reason="拒：短边624<640（§5.2）；且标2011疑现代重绘，不纠缠。"),
    "commons_Lady_Wang_mural_Mogao_cave_130_Detail_jpg": dict(decision="reject", reason="拒：短边600<640（§5.2）。"),
    "commons_Lady_Wang_mural_Mogao_cave_130_jpg": dict(decision="reject", reason="拒：短边448<640（§5.2）。"),
    "commons_Ivan_Bilibin_illustration_for_the_epic_volga_19041_jpg": dict(decision="reject", reason="拒：短边452<640（§5.2）。"),
    "commons_Volga_Bilibin_05_jpg": dict(decision="reject", reason="拒：短边370<640（§5.2）。"),

    # ---------- reject：段文杰1959临摹（段卒2011，临摹品权利未清，§2）----------
    "commons_Chatra_from_The_Governor_s_Wife_Offering_jpg": dict(decision="reject", reason="拒：1959 段文杰(卒2011)复原临摹品，临摹层权利未清（§2.1/§2.3）。"),
    "commons_Portrait_of_Lady_Wang_Governor_s_Wife_05_2013_12_JPG": dict(decision="reject", reason="拒：1959 段文杰复原临摹品（§2）。"),
    "commons_Portrait_of_Lady_Wang_Governor_s_Wife_05_2013_12_cropped_JPG": dict(decision="reject", reason="拒：1959 段文杰复原临摹品裁切版（§2）。"),
    "commons_jpg": dict(decision="reject", reason="拒：都督夫人礼佛图 1959 段文杰复原临摹品（§2）。"),

    # ---------- reject：照片/非艺术品 ----------
    "commons_Harry_Clarke_photo_jpg": dict(decision="reject", reason="拒：人物照片，非平面艺术品（§3.1）。"),
    "commons_Harry_Clarke_signature_jpg": dict(decision="reject", reason="拒：签名，非艺术品（§3.1）。"),
    "commons_L_on_Bakst_btv1b70020720_jpg": dict(decision="reject", reason="拒：Bakst 肖像照片（目检确认），非艺术品（§3.1）。"),
    "commons_L_on_Bakst_debout_dans_un_salon_d_appartement_photo_de_Choum": dict(decision="reject", reason="拒：照片（§3.1）。"),
    "commons_L_on_Bakst_en_tenue_de_peintre_un_crayon_dans_la_main_droite": dict(decision="reject", reason="拒：照片（§3.1）。"),

    # ---------- reject：风格不符（§3.1 风格匹配<4）----------
    "commons_E_S_Pits_Bilibina_by_K_Somov_1926_jpg": dict(decision="reject", reason="拒：Somov 现代肖像画，风格不匹配（§3.1）。"),
    "met_39895": dict(decision="reject", reason="拒：中国水墨卷轴，非矿物色平涂（§3.1）。"),
    "met_39901": dict(decision="reject", reason="拒：中国水墨（照夜白），非矿物色平涂（§3.1）。"),
    "met_40057": dict(decision="reject", reason="拒：中国水墨卷轴（§3.1）。"),
    "met_438821": dict(decision="reject", reason="拒：Gauguin 油画，风格不匹配（§3.1）。"),
    "met_446297": dict(decision="reject", reason="拒：al-Sufi 星图墨线素描+大面积斑驳，风格弱（§3.1/§5.2）；machine_or_sky 另找彩绘版。"),
    "met_450605": dict(decision="reject", reason="拒：Vali Jan 淡彩素描，矿物色不足（§3.1）。"),
    "met_451287": dict(decision="reject", reason="拒：书法页为主体（§3.1）。"),
    "met_453385": dict(decision="reject", reason="拒：书法页为主体（§3.1）。"),
    "met_470309": dict(decision="reject", reason="拒：欧洲 grisaille 抄本，非矿物色平涂（§3.1）。"),
    "met_626692": dict(decision="reject", reason="拒：欧洲古典油画（§3.1）。"),
    "met_701293": dict(decision="reject", reason="拒：中国书法/册页（§3.1）。"),
    "met_824771": dict(decision="reject", reason="拒：欧洲油画（§3.1）。"),
    "met_910384": dict(decision="reject", reason="拒：欧洲油画（§3.1）。"),

    # ---------- reject：2026-09-16 第三轮 ----------
    "met_435711": dict(decision="reject", reason="拒：欧洲东方主义油画（§3.1）。"),
    "met_435844": dict(decision="reject", reason="拒：Caravaggio 油画《The Musicians》，风格不匹配（§3.1）。"),
    "met_435997": dict(decision="reject", reason="拒：欧洲油画《The Storm》（§3.1）。"),
    "met_436105": dict(decision="reject", reason="拒：欧洲新古典油画《The Death of Socrates》（§3.1）。"),
    "met_436803": dict(decision="reject", reason="拒：欧洲宗教油画《The Adoration of the Magi》（§3.1）。"),
    "met_437508": dict(decision="reject", reason="拒：欧洲油画《Self-Portrait》（§3.1）。"),
    "met_437873": dict(decision="reject", reason="拒：Velázquez 油画《Philip IV》（§3.1）。"),
    "met_453895": dict(decision="reject", reason="拒：淡彩浅绛单页（Youth and Dervish），矿物色不足（§3.1，同 met_450605）。"),
    "commons_A_treatise_on_chess_2_jpg": dict(decision="reject", reason="拒：短边390<640（§5.2）。"),

    # ---------- train：water 主题（2026-09-16 第四轮）----------
    "commons_Khusraw_watches_Shirin_bathing_jpg": dict(
        decision="train", family="B", theme_primary="water",
        publication_year="1540",
        reason="人工目检可留：《Khusraw 窥 Shirin 沐浴》(Commons CC0，文件页 1539–1543，取1540)；莲池泳者+鱼+小舟+纹样山坡，平涂矿物色，B 族 water。"),
    "commons_16_2_8_2005_Noahs_ark_Hafis_Abru_2_jpg": dict(
        decision="train", family="B", theme_primary="water",
        publication_year="1430",
        reason="人工目检可留：帖木儿《诺亚方舟》(Commons PD，文件页 1405–1447，取1430)；金天+方舟载人畜+浪纹+海蛇，平涂矿物色，B 族 water。"),

    # ---------- reject：第四轮 ----------
    "commons_16_2_8_2005_Noahs_ark_Hafis_Abru_2_edit_JPG": dict(decision="reject", reason="拒：与 commons_16_2_8_2005_Noahs_ark_Hafis_Abru_2_jpg 同一图的编辑版，重复入库（§3.2）。"),
    "commons_Khusraw_spies_Shirin_bathing_38v_Tabriz_1501_1510_addition_b": dict(decision="reject", reason="拒：淡淡水彩，矿物色不足（§3.1，同 met_450605）。"),
    "commons_Aj_ib_al_makhl_q_t_Noah_s_Ark_and_a_Concentric_Square_f_260v": dict(decision="reject", reason="拒：短边451<640（§5.2）。"),
    "commons_Jonah_is_thrown_into_the_mouth_of_a_whale_Spieghel_der_mensc": dict(decision="reject", reason="拒：欧洲尼德兰抄本灰褐淡彩+文字栏，非矿物色平涂（§3.1，同 met_470309）。"),

    # ---------- train：water / nature / ornament（2026-09-16 第五轮）----------
    "commons_Brooklyn_Museum_Khusraw_Discovers_Shirin_Bathing_From_Pictor": dict(
        decision="review", family="B", theme_primary="water", train_filename="",
        reason="风格可留（Khusraw 发现 Shirin 沐浴，池泳者+鱼+舟+马队，B 族 water）；但原图仅 768x760，短边 760 < 768，达不到 16gb 剖面门槛（§5.2），移出训练集暂存 data/crops/_hold（换高清源再入册）。"),
    "commons_Shahnameh_illustration_IMJ_B69_0633_jpeg": dict(
        decision="review", family="B", theme_primary="nature",
        reason="风格可留（持旗矛骑者过山，纹样树石满铺，B 族 nature）；但 Commons 元数据只给上传日期2018，无作品年代证据，按 §2.1 退回 review——补到年代再入册（三件套暂存 data/crops/_hold）。"),
    "commons_Shahnameh_illustration_IMJ_B69_0627_jpeg": dict(
        decision="review", family="B", theme_primary="nature",
        reason="风格可留（骑者与旗帜穿行山隘，B 族 nature）；但 Commons 元数据只给上传日期2018，无作品年代证据，按 §2.1 退回 review——补到年代再入册（三件套暂存 data/crops/_hold）。"),
    "commons_Tawaraya_Sotatsu_Waves_at_Matsushima_2_Google_Art_Project_jp": dict(
        decision="train", family="E", theme_primary="water",
        publication_year="1620",
        reason="人工目检可留：俵屋宗达《松岛图》另一扇(Commons PD，Google Art Project，取1620)；金地浪脊+松岩，E 族 water；与 00028 同屏风不同扇（§3.2 同一屏风限 3 张）。"),
    "commons_The_Fire_Ordeal_of_Siyawush_from_a_Shahnama_of_Firdawsi_Safa": dict(decision="train", family="B", theme_primary="ritual", publication_year="1575", reason="人工目检可留：《Siyavush 火审》(Commons PD，文件页16世纪后半，取1575)；骑者穿越火海+帐幕下观众，B 族 ritual。"),
    "commons_Soutatsu_Matsushima_jpg": dict(decision="reject", reason="拒：短边439<640（§5.2）。"),
    "commons_Boats_upon_Waves_MET_DP264141_jpg": dict(decision="train", family="E", theme_primary="water", creator_death_year="1643", reason="人工目检可留：《波に舟図屏風》(Met CC0, DP264141)；金地绿蓝浪脊+小舟，E 族 water。"),
    "commons_Boats_upon_Waves_MET_DP262119_jpg": dict(decision="train", family="E", theme_primary="water", creator_death_year="1643", reason="人工目检可留：《波に舟図屏風》(Met CC0, DP262119)；金地堆叠浪脊+小舟，E 族 water。"),
    "commons_Boats_upon_Waves_MET_49_35_3_d_jpg": dict(decision="train", family="E", theme_primary="water", creator_death_year="1643", reason="人工目检可留：《波に舟図屏風》(Met CC0, 49.35.3d)；金地卷浪+载人之舟，E 族 water。"),
    "commons_Enthronement_of_Luhrasp_Iran_17th_century_jpg": dict(decision="train", family="B", theme_primary="court", publication_year="1650", reason="人工目检可留：《Luhrasp 登基》(Commons PD，文件页标伊朗17世纪，取1650)；宝座帐顶+廷臣列，B 族 court。"),
    "commons_Banner_with_Bodhisattva_possibly_Mahamayuri_jpg": dict(decision="train", family="A", theme_primary="ritual", publication_year="900", reason="人工目检可留：敦煌幡画《菩萨立像》(Commons PD，取900)；莲台宝冠+条纹裙+团花带，平涂矿物色，A 族 ritual。"),
    "commons_Painting_of_the_folk_tale_Sohni_Mahiwal_Mughal_ca_1700_50_jp": dict(decision="train", family="B", theme_primary="court", publication_year="1725", reason="人工目检可留：《Sohni-Mahiwal》上部宫廷集会(Commons PD，文件页 ca.1700-50，取1725)；金天+宫台+廷臣+花树，B 族 court；裁上部画幅带。"),
    "commons_KorinsScreen_webp": dict(decision="train", family="E", theme_primary="nature", publication_year="1710", reason="人工目检可留：光琳屏风《梅树》(Commons PD，取1710)；金地白梅+虬枝+下方水纹带，E 族 nature。"),
    "commons_Boats_upon_Waves_MET_DP262129_jpg": dict(decision="train", family="E", theme_primary="water", creator_death_year="1643", reason="人工目检可留：《波に舟図屏風》另一扇(Met CC0, DP262129，宗达卒1643)；金地浪脊+松岛小舟，E 族 water。"),
    "commons_K_rin_Matsushima_jpg": dict(decision="train", family="E", theme_primary="water", creator_death_year="1716", reason="人工目检可留：尾形光琳《松岛图》(Commons PD，光琳卒1716)；金地梳状浪纹+绿赭岩岛+黑松，E 族 water；替换短边不足的 00024。"),
    "met_74906": dict(decision="train", family="A", theme_primary="ritual", reason="人工目检可留：敦煌绢画《观音说法图》(Met CC0 74906)；红地华盖+幡幢+云气卷草，A 族 ritual。"),
    "commons_Jonah_and_the_Whale_Folio_from_a_Jami_al_Tavarikh_Compendium": dict(decision="train", family="B", theme_primary="nature", publication_year="1400", reason="人工目检可留：《约拿出鱼口》页(Commons PD，Jami al-Tavarikh，取1400)；花树+有翼侍者+山石草木，B 族 nature。"),
    "commons_Kalila_wa_Dimna_1_jpg": dict(decision="train", family="B", theme_primary="nature", publication_year="1500", reason="人工目检可留：Kalila wa Dimna 寓言插图(Commons PD，取1500)；花树下豺+枝头鸟+山石花草，B 族 nature。"),
    "met_78195": dict(decision="train", family="A", theme_primary="ritual", reason="人工目检可留：护法神 Mahakala(Met CC0 78195)；深蓝地火焰卷涡背光，中心向外轮环，A 族 ritual。"),
    "commons_Courtiers_present_gifts_to_a_ruler_Safavid_Shiraz_Iran_circa": dict(decision="train", family="B", theme_primary="court", publication_year="1600", reason="人工目检可留：萨法维设拉子《廷臣献礼》(Commons PD，文件页 circa 1600)；宝座帐顶+金器+花卉地毯，B 族 court。"),
    "commons_Court_of_the_Indian_King_Heblar_from_a_Mongol_period_Kalila": dict(decision="train", family="B", theme_primary="court", publication_year="1350", reason="人工目检可留：Kalila wa Dimna《印度王 Heblar 的宫廷》(Commons PD，取1350)；宝座+廷臣+花鸟，B 族 court。"),
    "met_854908": dict(decision="train", family="A", theme_primary="ritual", reason="人工目检可留：Vaishravana 天王(Met CC0 854908)；绿头光+鱼鳞甲+红地卷云，A 族 ritual。"),
    "commons_Binding_for_the_Mantiq_al_tayr_Language_of_the_Birds_MET_DP2": dict(decision="train", family="F", theme_primary="ornament", publication_year="1600", reason="人工目检可留：Mantiq al-tayr 皮面装帧(Met CC0，文件页 circa 1600)；金压印团花+阿拉贝斯+边饰，无情节，F 族 ornament。"),
    "commons_Rough_waves_Ogata_K_rin_jpg": dict(decision="reject", reason="拒：水墨浪纹+题字，非矿物色平涂（§3.1，同 met_39901）。"),
    "commons_Iranian_Courtiers_of_Shah_Abbas_I_Walters_W691A_jpg": dict(decision="train", family="B", theme_primary="court", publication_year="1650", reason="人工目检可留：《阿拔斯一世宫廷群像》(Walters W691A, Commons PD，文件页 Safavid 17世纪，取1650)；廷臣列+持鹰者+花树地毯，B 族 court。"),
    "commons_Waves_at_Matsushima_jpg": dict(decision="reject", reason="拒：黑白珂罗版印刷复制品（§5.2 翻拍/黑白）。"),
    "commons_Kalila_Upbraiding_Dimna_Folio_from_a_Kalila_wa_Dimna_MET_DP": dict(decision="train", family="B", theme_primary="nature", publication_year="1750", reason="人工目检可留：Kalila wa Dimna《Kalila 斥 Dimna》(Met CC0，文件页18世纪，取1750)；双豺对峙+棕榈+纹样坡地，B 族 nature。"),
    "commons_Tawaraya_Sotatsu_Waves_at_Matsushima_Google_Art_Project_jpg": dict(
        decision="train", family="E", theme_primary="water",
        publication_year="1620",
        reason="人工目检可留：俵屋宗达《松岛图》屏风(Commons PD，Google Art Project，宗达活跃至约1643，取1620)；金地+蓝绿浪脊+松岛，水纹纯图案化，E 族 water。"),
    "commons_Muraqqa_e_Golshan_Page_106_jpg": dict(
        decision="train", family="F", theme_primary="ornament",
        publication_year="1600",
        reason="人工目检可留：Muraqqa-e Golshan 第106页上部金饰面板(Commons PD)；蓝地金阿拉贝斯+红金团花，无情节，F 族 ornament；裁上部图案区。"),
}


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    shutil.copy2(CSV, CSV.with_suffix(".bak.csv"))
    n_train = n_rej = n_keep = 0
    for r in rows:
        fid = r["file_id"]
        t = T.get(fid)
        if not t:
            n_keep += 1
            print("  ?? 未判定（保持原样）：%s" % fid)
            continue
        for k in ("decision", "family", "theme_primary", "reason", "train_filename",
                  "creator", "creator_death_year", "publication_year"):
            if k in t:
                r["family" if k == "family" else
                  "theme_primary" if k == "theme_primary" else
                  "decision_reason" if k == "reason" else k] = t[k]
        if t["decision"] == "train":
            n_train += 1
        elif t["decision"] == "reject":
            n_rej += 1
            src = RAW / fid
            if src.is_dir():
                REJ.mkdir(parents=True, exist_ok=True)
                dst = REJ / fid
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(src), str(dst))
    with open(CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})

    # 清理：空目录 / 目检缩略图
    empty = RAW / "met_551786"
    if empty.is_dir() and not any(empty.iterdir()):
        empty.rmdir()
        print("  清理空目录 met_551786")
    for th in RAW.glob("*/_thumb.png"):
        th.unlink()
        print("  清理缩略图 %s" % th.parent.name)

    print("-" * 60)
    print("triage 落盘：train=%d, reject=%d, 未触及=%d（备份 provenance.bak.csv）" % (n_train, n_rej, n_keep))
    tr = [r for r in rows if r.get("decision") == "train"]
    print("train 明细：")
    for r in tr:
        print("  %-58s %-2s %-8s %sx%s" % (r["file_id"], r.get("family") or "?",
                                          r.get("theme_primary") or "?",
                                          r.get("width"), r.get("height")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
