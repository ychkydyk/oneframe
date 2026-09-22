# -*- coding: utf-8 -*-
"""Перепроверка вызова deadpool-hermes (#47842): почему на цели 1 Мбит выходит 0.08.

Меряем ТРИ вещи по каждому кодированию, чтобы отделить баг метода от поведения x264:
  target   что заказали (-b:v)
  actual   что реально в файле (размер*8/длительность)
  qp/flat  схлопнулись ли кадры в почти-плоские (средняя дисперсия яркости)

Гипотеза deadpool: на шуме ratecontrol обязан ЗАЛИТЬ бюджет, недобор до 8% = цель
не поставлена. Наша встречная: на цели, далеко НИЖЕ содержания, квантование бьёт в
потолок, остаток исчезает, кадр становится плоским — и битрейт падает НИЖЕ цели не
из-за игнора цели, а потому что заливать уже нечего.

Плюс лестница CRF 18..28 — как люди реально экспортируют.
"""
import json, os, subprocess, tempfile

def прогон(cmd):
    return subprocess.run(cmd, capture_output=True)

def инфо(путь):
    r = subprocess.run(["ffprobe","-v","error","-print_format","json","-show_format","-show_streams",путь],
                       capture_output=True,text=True,encoding="utf-8",errors="replace")
    return json.loads(r.stdout)

def плоскость(путь):
    """Средняя дисперсия яркости по 4 кадрам: ~0 = кадры схлопнулись в плоские."""
    import numpy as np
    d=инфо(путь); длит=float(d.get("format",{}).get("duration") or 6)
    дисп=[]
    with tempfile.TemporaryDirectory() as t:
        for i in range(4):
            f=os.path.join(t,"k%d.png"%i)
            прогон(["ffmpeg","-v","error","-ss","%.2f"%(длит*(i+0.5)/4),"-i",путь,"-frames:v","1","-y",f])
            if os.path.exists(f):
                try:
                    import cv2
                    g=cv2.imdecode(np.fromfile(f,dtype=np.uint8),cv2.IMREAD_GRAYSCALE).astype(float)
                    дисп.append(float(g.var()))
                except Exception: pass
    return sum(дисп)/len(дисп) if дисп else None

def битрейт(путь,длит): return os.path.getsize(путь)*8/длит/1e6  # Мбит/с

def main():
    раб=tempfile.mkdtemp(prefix="brchk_")
    ист=os.path.join(раб,"src.mkv")
    прогон(["ffmpeg","-v","error","-f","lavfi","-i",
            "nullsrc=s=1920x1080:d=6:r=30,geq=lum='random(1)*255':cb=128:cr=128,format=gray",
            "-c:v","ffv1","-y",ист])
    длит=6.0
    print("исходник:", "%.2f Мбит/с эффективный (ffv1 lossless)"%битрейт(ист,длит),
          "| дисперсия яркости %.0f"%(плоскость(ист) or 0))
    print("\n== цель против факта ==")
    print("%6s %10s %10s %14s" % ("цель","факт","факт/цель","дисперсия кадра"))
    for м in (1,2,4,8,16,32):
        f=os.path.join(раб,"b%d.mp4"%м)
        прогон(["ffmpeg","-v","error","-i",ист,"-c:v","libx264","-preset","medium",
                "-b:v","%dM"%м,"-maxrate","%dM"%м,"-bufsize","%dM"%(м*2),
                "-pix_fmt","yuv420p","-y",f])
        if not os.path.exists(f): print("%6d  НЕ СОЗДАН"%м); continue
        факт=битрейт(f,длит); дисп=плоскость(f)
        print("%5dM %9.2fM %9d%% %14.0f" % (м, факт, round(100*факт/м), дисп or 0))
    print("\n== CRF-лестница (как экспортируют люди) ==")
    print("%6s %10s %14s" % ("crf","факт Мбит","дисперсия"))
    for c in (18,20,23,26,28):
        f=os.path.join(раб,"c%d.mp4"%c)
        прогон(["ffmpeg","-v","error","-i",ист,"-c:v","libx264","-preset","medium",
                "-crf",str(c),"-pix_fmt","yuv420p","-y",f])
        if os.path.exists(f):
            print("%6d %9.2fM %14.0f" % (c, битрейт(f,длит), плоскость(f) or 0))
    print("\nрабочая папка:",раб)

if __name__=="__main__": main()
