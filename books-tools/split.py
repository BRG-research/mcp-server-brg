import numpy as np
from PIL import Image
from multiprocessing import Pool
Image.MAX_IMAGE_PIXELS=None
def off(i): return -36 if i<166 else (-38 if i<235 else -40)
def gutter(im):
    g=np.asarray(im.convert('L').resize((im.width//4,im.height//4))).astype(float)
    w=g.shape[1]; band=g[:, int(w*0.40):int(w*0.60)].mean(0)
    return (int(w*0.40)+int(np.argmin(band)))*4
def go(i):
    if i in (166,234): return []
    im=Image.open(f'crop2/c{i:03d}.jpg'); w,h=im.size; gx=gutter(im)
    out=[]
    for side,box in (('L',(0,0,gx+40,h)),('R',(gx-40,0,w,h))):
        p=im.crop(box)
        if 18<=i<=294:
            num=2*i+off(i)+(0 if side=='L' else 1); name=f'p{num:04d}'
        else:
            name=f'scan{i:03d}{side}'
        if i>=295: continue
        hh=p.height; ov=120
        p.crop((0,0,p.width,hh//2+ov)).save(f'work/pages/{name}a.jpg',quality=88)
        p.crop((0,hh//2-ov,p.width,hh)).save(f'work/pages/{name}b.jpg',quality=88)
        out.append(name)
    return out
if __name__=='__main__':
    with Pool(14) as pl: r=pl.map(go,range(0,323))
    names=[n for x in r for n in x]; print(len(names), names[:3], names[-3:])
    # plates
    roman=['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII','XIII','XIV','XV','XVI','XVII','XVIII','XIX','XX','XXI','XXII','XXIII','XXIV','XXV','XXVI']
    scans=[s for s in range(296,323) if s!=309]
    for k,s in enumerate(scans):
        im=Image.open(f'crop2/c{s:03d}.jpg'); im.save(f'work/plates/Pl{k+1:02d}.jpg',quality=92)
    print(dict(zip(roman,scans)))
