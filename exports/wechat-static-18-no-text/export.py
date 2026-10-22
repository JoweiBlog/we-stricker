"""Export eighteen original character poses without caption text."""
from pathlib import Path
import csv
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED
import numpy as np
from scipy.ndimage import label, find_objects
from PIL import Image

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SHEETS = [
    ('首套九宫格概念图.png', ['来了','收到','冲鸭','委屈','呜呜','啊','累了','爱你','晚安'],
     [0,410,790,1199], [[0,437,875,1312],[0,400,910,1312],[0,420,875,1312]]),
    ('第二套九宫格静态衍生图.png', ['得意','害羞','震惊','嫌弃','生气','期待','无语','加油','谢谢'],
     [0,410,785,1199], [[0,437,875,1312]]*3),
]
records=[]
previews=[]
for sheet_index,(filename,names,rows,columns) in enumerate(SHEETS):
    sheet=Image.open(PROJECT/'assets/concepts'/filename).convert('RGB')
    assert sheet.size==(1312,1199)
    for k,name in enumerate(names):
        r,c=divmod(k,3)
        body_bottom = ([329, 711, 1084] if sheet_index == 0 else [327, 711, 1084])[r]
        rect=(columns[r][c],rows[r],columns[r][c+1],body_bottom)
        tile=sheet.crop(rect)
        # Caption tops are not aligned across cells. Remove any residual caption
        # fragments below the substantial character/prop components.
        pixels=np.asarray(tile).astype(int)
        foreground=(pixels.min(2)<180)|((pixels.max(2)-pixels.min(2)>24)&(pixels.min(2)<235))
        labels,nlabels=label(foreground)
        sizes=np.bincount(labels.ravel())
        objects=find_objects(labels)
        floor=max(ob[0].stop for i,ob in enumerate(objects,1) if ob is not None and sizes[i]>=1000)
        tile=tile.crop((0,0,tile.width,floor))
        a=np.asarray(tile).astype(int)
        # Include fur, gray weapons, text and colored accents; ignore faint shadows.
        mask=(a.min(2)<180)|((a.max(2)-a.min(2)>24)&(a.min(2)<235))
        components,n=label(mask)
        counts=np.bincount(components.ravel())
        good=counts>=8;good[0]=False
        ys,xs=np.where(good[components])
        box=(max(0,int(xs.min())-6),max(0,int(ys.min())-6),
             min(tile.width,int(xs.max())+7),min(tile.height,int(ys.max())+7))
        content=tile.crop(box)
        scale=min(224/content.width,224/content.height)
        resized=content.resize((round(content.width*scale),round(content.height*scale)),Image.Resampling.LANCZOS)
        out=Image.new('RGB',(240,240),'white')
        out.paste(resized,((240-resized.width)//2,(240-resized.height)//2))
        number=sheet_index*9+k+1
        path=ROOT/f'{number:02d}-{name}.png'
        out.save(path,optimize=True)
        assert path.stat().st_size<500000
        with Image.open(path) as test:
            assert test.size==(240,240) and test.format=='PNG' and test.mode=='RGB'
        records.append({'id':f'{number:02d}','name':name,'meaning':name,'tags':['卖萌'],
                        'file':path.name,'width':240,'height':240,'bytes':path.stat().st_size,
                        'source':filename,'crop_region':rect,
                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        previews.append(out)

assert len(records)==18
(ROOT/'manifest.json').write_text(json.dumps({'purpose':'微信表情单品上传','format':'PNG','background':'white','caption_text':False,'stickers':records},ensure_ascii=False,indent=2)+'\n')
with (ROOT/'上传信息.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f,lineterminator="\n");writer.writerow(['编号','文件名','含义词','标签','尺寸','文件大小（字节）'])
    for item in records:writer.writerow([item['id'],item['file'],item['meaning'],'、'.join(item['tags']),'240×240',item['bytes']])
preview=Image.new('RGB',(240*6,240*3),'white')
for i,im in enumerate(previews):preview.paste(im,((i%6)*240,(i//6)*240))
preview.save(ROOT/'18款无字预览.jpg',quality=93)
zip_path=ROOT/'我的刀盾-18款无字微信表情.zip'
with ZipFile(zip_path,'w',compression=ZIP_DEFLATED) as archive:
    for item in records:archive.write(ROOT/item['file'],item['file'])
    archive.write(ROOT/'上传信息.csv','上传信息.csv')
    archive.write(ROOT/'manifest.json','manifest.json')
print('Exported 18 verified PNGs; min/max bytes:',min(i['bytes'] for i in records),max(i['bytes'] for i in records))
print(zip_path)
