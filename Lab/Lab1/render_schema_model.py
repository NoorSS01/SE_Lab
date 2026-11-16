from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

OUT = Path('/home/ubuntu')
W, H = 3200, 2100
BG, WHITE, MUTED = '#0d0f10', '#f4f4f4', '#c9ced0'
ACCENT, LINE, GRID = '#59d5c7', '#aeb8ba', '#dfe5e6'
NOTE_BG = '#171b1c'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
def F(size, bold=False, mono=False):
    return ImageFont.truetype(MONO if mono else (BOLD if bold else FONT), size)

img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)
d.text((80, 34), 'CORRECTED INVENTORY RISK & DEMAND ANALYSIS — RELATIONAL SCHEMA MODEL', fill=WHITE, font=F(34, True))
d.text((80, 82), 'Primary keys are underlined; foreign keys are marked [FK]. Associative tables resolve all M:N relationships.', fill=MUTED, font=F(22))
d.line((80, 124, W-80, 124), fill='#3a4547', width=2)

# name: (fields, x, y). The row format intentionally mirrors the supplied reference schema image.
TABLES = {
'CUSTOMER': ([("Customer_ID",'PK'),('Customer_Name','A'),('Customer_Type','A'),('Email','A'),('Phone_Number','A'),('Address','A'),('Is_Active','A')], 90, 165),
'SALES_ORDER': ([("SO_ID",'PK'),('Customer_ID [FK]','FK'),('Warehouse_ID [FK]','FK'),('Order_Date','A'),('Required_Date','A'),('Status','A'),('Total_Amount','A')], 1630, 165),
'SO_ITEM': ([("SO_Item_ID",'PK'),('SO_ID [FK]','FK'),('Product_ID [FK]','FK'),('Quantity','A'),('Unit_Price','A'),('Discount','A'),('Tax_Amount','A'),('Line_Total','A')], 90, 365),
'DEMAND_HISTORY': ([("Demand_ID",'PK'),('SO_Item_ID [FK]','FK'),('Product_ID [FK]','FK'),('Warehouse_ID [FK]','FK'),('Demand_Date','A'),('Quantity_Demanded','A'),('Days_of_Stock','A'),('Demand_Trend','A'),('Reorder_Level','A')], 1120, 365),
'PRODUCT': ([("Product_ID",'PK'),('SKU','A'),('Product_Name','A'),('Brand','A'),('Barcode','A'),('Category_ID [FK]','FK'),('UOM_ID [FK]','FK'),('Unit_Price','A'),('Reorder_Level','A'),('Discontinued_Flag','A')], 90, 565),
'CATEGORY': ([("Category_ID",'PK'),('Category_Name','A'),('Parent_Category_ID [FK]','FK'),('Description','A'),('Is_Active','A')], 1630, 565),
'UOM': ([("UOM_ID",'PK'),('UOM_Name','A'),('UOM_Type','A'),('Base_UOM_ID [FK]','FK')], 2460, 565),
'SUPPLIER_PRODUCT': ([("Supplier_Product_Code",'PK'),('Supplier_ID [FK]','FK'),('Product_ID [FK]','FK'),('Unit_Cost','A'),('Lead_Time_Days','A'),('Is_Preferred','A')], 90, 765),
'SUPPLIER': ([("Supplier_ID",'PK'),('Supplier_Name','A'),('Contact_Person','A'),('Email','A'),('Phone_Number','A'),('Address','A'),('Rating','A'),('Is_Active','A')], 1420, 765),
'PURCHASE_ORDER': ([("PO_ID",'PK'),('Supplier_ID [FK]','FK'),('PO_Date','A'),('Expected_Date','A'),('Status','A'),('Total_Amount','A')], 2200, 765),
'PO_ITEM': ([("PO_Item_ID",'PK'),('PO_ID [FK]','FK'),('Product_ID [FK]','FK'),('Quantity','A'),('Unit_Cost','A'),('Tax_Amount','A'),('Line_Total','A')], 90, 965),
'INVENTORY': ([("Inventory_ID",'PK'),('Product_ID [FK]','FK'),('Warehouse_ID [FK]','FK'),('Quantity_On_Hand','A'),('Reserved_Quantity','A'),('Available_Quantity','A'),('Min_Stock_Level','A'),('Max_Stock_Level','A'),('Reorder_Level','A'),('Location_Slot','A'),('Last_Updated','A'),('Is_Active','A')], 1040, 965),
'WAREHOUSE': ([("Warehouse_ID",'PK'),('Warehouse_Name','A'),('Capacity','A'),('Is_Active','A')], 2410, 965),
'STOCK_MOVEMENT': ([("Movement_ID",'PK'),('Inventory_ID [FK]','FK'),('Reason_ID [FK]','FK'),('Movement_Date','A'),('Movement_Type','A'),('Quantity','A'),('Reference_Type','A'),('Reference_ID','A'),('Created_By','A')], 90, 1165),
'ADJUSTMENT_REASON': ([("Reason_ID",'PK'),('Reason_Type','A'),('Description','A'),('Affects_Inventory_Flag','A')], 1510, 1165),
'INVENTORY_RISK': ([("Risk_ID",'PK'),('Inventory_ID [FK]','FK'),('Risk_Type','A'),('Risk_Level','A'),('Risk_Score','A'),('Threshold_Value','A'),('Detected_Date','A'),('Recommended_Action','A'),('Status','A')], 90, 1365),
'STOCK_TRANSFER': ([("Transfer_ID",'PK'),('Product_ID [FK]','FK'),('From_Warehouse_ID [FK]','FK'),('To_Warehouse_ID [FK]','FK'),('Quantity','A'),('Transfer_Date','A')], 1500, 1365),
'DEMAND_FORECAST': ([("Forecast_ID",'PK'),('Product_ID [FK]','FK'),('Warehouse_ID [FK]','FK'),('Forecast_Date','A'),('Forecast_Horizon','A'),('Forecast_Quantity','A'),('Model_Name','A'),('Accuracy_Score','A'),('Created_Date','A')], 90, 1650),
}

ROW_H, NAME_W, CELL_W = 76, 230, 125
BOXES = {}
def table_width(fields): return NAME_W + CELL_W * len(fields)
for name, (fields, x, y) in TABLES.items():
    BOXES[name] = (x, y, x + table_width(fields), y + ROW_H)

# Labeled orthogonal paths. Endpoints are table edges; FK columns in the rows identify the exact referenced key.
def arrowhead(px, py, tx, ty):
    ang = math.atan2(ty-py, tx-px); s = 12
    d.polygon([(tx,ty), (tx-s*math.cos(ang-.48),ty-s*math.sin(ang-.48)), (tx-s*math.cos(ang+.48),ty-s*math.sin(ang+.48))], fill=LINE)
def connector(points, label, lx, ly):
    d.line(points, fill=LINE, width=3, joint='curve')
    arrowhead(points[-2][0], points[-2][1], points[-1][0], points[-1][1])
    bb = d.textbbox((0,0), label, font=F(17, True)); pad=5
    d.rounded_rectangle((lx-pad,ly-pad,lx+bb[2]-bb[0]+pad,ly+bb[3]-bb[1]+pad), radius=5, fill=NOTE_BG, outline='#3a7773', width=1)
    d.text((lx,ly), label, fill=ACCENT, font=F(17, True))

# Connectors are drawn first so they pass behind the schema rows, as in the reference image.
PATHS = [
((320,203),(1630,203),'PLACES',1080,145),
((1860,241),(1860,365),'CONTAINS',1870,300),
((470,641),(470,365),'ORDERED_IN',490,310),
((1050,403),(1120,403),'RECORDS',1040,335),
((840,641),(1120,441),'HAS',940,605),
((2530,965),(2530,441),'RECORDS',2550,610),
((1630,603),(840,603),'CATEGORIZES',1190,555),
((1860,641),(1860,690),'HAS_PARENT',1960,680),
((2460,603),(900,603),'MEASURES',2050,520),
((2760,641),(2760,700),'BASE_UOM',2670,680),
((1420,803),(1140,803),'OFFERS',1290,745),
((840,641),(840,803),'OFFERED_AS',890,735),
((2060,803),(2200,803),'RECEIVES',2080,745),
((2200,841),(2200,965),'CONTAINS',2240,910),
((840,641),(840,965),'ORDERED_AS',870,915),
((840,641),(1040,1003),'STORED_IN',900,930),
((2410,1003),(2200,1003),'HOUSES',2260,1035),
((1040,1003),(800,1203),'AFFECTS',850,1115),
((1510,1203),(1290,1203),'HAS_REASON',1320,1145),
((1160,1041),(800,1403),'HAS_RISK',920,1275),
((840,641),(1500,1403),'TRANSFERS',1170,1285),
((2410,1041),(2200,1403),'TRANSFER_FROM',2240,1260),
((2410,1041),(2580,1403),'TRANSFER_TO',2550,1260),
((2410,1003),(2900,241),'FULFILLS',2740,575),
]
for p1,p2,label,lx,ly in PATHS:
    if p1[0] == p2[0]:
        connector([p1,p2],label,lx,ly)
    else:
        mx = (p1[0]+p2[0])//2
        connector([p1,(mx,p1[1]),(mx,p2[1]),p2],label,lx,ly)
# Recursive category loop, deliberately offset from the table rows.
d.line([(1860,641),(1940,641),(1940,720),(1860,720),(1860,641)], fill=LINE, width=3)
arrowhead(1860,720,1860,641)
d.text((1950,704), 'HAS_PARENT', fill=ACCENT, font=F(17, True))

# Schema rows.
for name, (fields, x, y) in TABLES.items():
    d.rectangle((x,y,x+NAME_W,y+ROW_H), outline=GRID, width=3, fill='#131718')
    title_size = 15 if len(name) > 14 else (17 if len(name) > 10 else 22)
    d.text((x+10,y+28), name, fill=WHITE, font=F(title_size, True))
    cx = x + NAME_W
    for label, kind in fields:
        d.rectangle((cx,y,cx+CELL_W,y+ROW_H), outline=GRID, width=2, fill=BG)
        col = ACCENT if kind == 'FK' else WHITE
        txt = label.replace(' [FK]', '\n[FK]') if len(label) > 16 else label
        fnt = F(16, mono=True)
        lines = txt.split('\n')
        total_h = len(lines)*19
        for j, line_text in enumerate(lines):
            bb = d.textbbox((0,0), line_text, font=fnt)
            tx = cx + (CELL_W-(bb[2]-bb[0]))/2
            ty = y + (ROW_H-total_h)/2 + j*19 - 2
            d.text((tx,ty), line_text, fill=col, font=fnt)
        # Underline primary and foreign keys, matching the reference convention.
        bb = d.textbbox((0,0), lines[0], font=fnt)
        d.line((cx+(CELL_W-(bb[2]-bb[0]))/2, y+54, cx+(CELL_W+(bb[2]-bb[0]))/2, y+54), fill=ACCENT, width=2)
        cx += CELL_W

# Corrections panel.
panel_x,panel_y,panel_w,panel_h = 2060,1580,1050,425
d.rounded_rectangle((panel_x,panel_y,panel_x+panel_w,panel_y+panel_h), radius=14, fill=NOTE_BG, outline='#4d6668', width=2)
d.text((panel_x+24,panel_y+20), 'CORRECTIONS APPLIED', fill=ACCENT, font=F(25, True))
items = [
'STOCK_MOVEMENT affects INVENTORY, not CUSTOMER.',
'SO_ITEM records DEMAND_HISTORY from actual sales.',
'SALES_ORDER stores Warehouse_ID [FK] for FULFILLS.',
'CATEGORY includes Parent_Category_ID [FK] / HAS_PARENT.',
'Unclear demand names replaced by HAS / RECORDS.',
'M:N paths use SUPPLIER_PRODUCT, SO_ITEM, and PO_ITEM.',
'INVENTORY_RISK, DEMAND_HISTORY, DEMAND_FORECAST, and',
'STOCK_TRANSFER are retained for risk and demand analysis.'
]
for i,t in enumerate(items): d.text((panel_x+26,panel_y+65+i*39), f'{i+1}  {t}', fill=WHITE, font=F(17, mono=True))
d.text((panel_x+26,panel_y+375), 'DEMAND_FORECAST is explicitly retained as a required analytical entity.', fill='#e0bd73', font=F(15))
d.text((80,H-48), 'Schema model generated from the supplied ER diagram | Corrected FK-based relational design | Aug 2026', fill='#8f9a9c', font=F(18))

img.save(OUT/'corrected_schema_model.png', quality=95)
print(OUT/'corrected_schema_model.png')
print(f'{len(TABLES)} tables, {len(PATHS)} labeled relationships')
