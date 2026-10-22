"""Export the eighteen confirmed V2 poses without changing original artwork."""
from pathlib import Path
from PIL import Image
from scipy.ndimage import label
import numpy as np
import json, csv, hashlib
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
SHEETS=[
 ('第二版-日常社交-无字九宫格.png',['抱抱','拜托','对不起','吃瓜','摸鱼','溜了','自闭','拿捏','好耶'],
  [[0,437,875,1312],[0,437,875,1312],[0,490,875,1312]]),
 ('第二版-第二组-无字九宫格.png',['点赞','拒绝','惊喜','馋了','怕冷','怕热','嘘','敬礼','摔倒'],
  [[0,437,875,1312],[0,437,875,1312],[0,437,830,1312]])]
rows=[0,380,740,1199]
records=[];previews=[]
(ROOT/'stickers').mkdir(exist_ok=True)
for group,(source,names,columns) in enumerate(SHEETS,1):
 sheet=Image.open(PROJECT/'assets/v2-social'/source).convert('RGB')
 assert sheet.size==(1312,1199)
 for i,name in enumerate(names):
  r,c=divmod(i,3);region=(columns[r][c],rows[r],columns[r][c+1],rows[r+1])
  tile=sheet.crop(region);a=np.asarray(tile).astype(int)
  mask=(a.min(2)<180)|((a.max(2)-a.min(2)>24)&(a.min(2)<235))
  comp,n=label(mask);counts=np.bincount(comp.ravel());keep=counts>=8;keep[0]=False
  ys,xs=np.where(keep[comp])
  box=(max(0,int(xs.min())-5),max(0,int(ys.min())-5),min(tile.width,int(xs.max())+6),min(tile.height,int(ys.max())+6))
  tile=tile.crop(box);scale=min(224/tile.width,224/tile.height)
  tile=tile.resize((round(tile.width*scale),round(tile.height*scale)),Image.Resampling.LANCZOS)
  out=Image.new('RGB',(240,240),'white');out.paste(tile,((240-tile.width)//2,(240-tile.height)//2))
  number=(group-1)*9+i+1;file=f'stickers/{number:02d}-{name}.png';path=ROOT/file
  out.save(path,optimize=True)
  assert path.stat().st_size<500000
  with Image.open(path) as check:assert check.size==(240,240) and check.format=='PNG'
  records.append({'id':f'{number:02d}','name':name,'meaning':name,'tags':['卖萌'],'status':'approved','approved_date':'2026-10-22','group':group,'file':file,'width':240,'height':240,'bytes':path.stat().st_size,'source':source,'crop_region':region,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
  previews.append(out)
assert len(records)==18
manifest={'project':'我的刀盾','version':'2.0','status':'approved','no_caption_text':True,'selected_departure_pose':'第一稿抱盾小跑，未采用踩盾滑行修订','stickers':records}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with (ROOT/'上传信息.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.writer(f,lineterminator='\n');writer.writerow(['编号','文件名','含义词','标签','尺寸','大小（字节）'])
 for item in records:writer.writerow([item['id'],item['file'],item['meaning'],'、'.join(item['tags']),'240×240',item['bytes']])
preview=Image.new('RGB',(1440,720),'white')
for i,im in enumerate(previews):preview.paste(im,((i%6)*240,(i//6)*240))
preview.save(ROOT/'第二版18款预览.jpg',quality=93)
with ZipFile(ROOT/'我的刀盾-第二版18款无字表情.zip','w',compression=ZIP_DEFLATED) as z:
 for item in records:z.write(ROOT/item['file'],item['file'])
 for name in ['manifest.json','上传信息.csv']:z.write(ROOT/name,name)
print('18 verified V2 PNGs;',min(i['bytes'] for i in records),'-',max(i['bytes'] for i in records),'bytes each')
