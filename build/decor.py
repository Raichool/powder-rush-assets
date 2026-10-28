import bpy,bmesh,math,json,os
from mathutils import Vector as V, Matrix as M
R=math.radians
RAW='/workspace/powder-assets/raw'; OUT='/workspace/powder-assets/out/decor_raw'; os.makedirs(OUT,exist_ok=True)
N=RAW+'/kenney-nature-kit/Models/GLTF format/'; H=RAW+'/kenney-holiday-kit/Models/GLB format/'; QN=RAW+'/stylized-nature-megakit/glTF/'
hx=lambda h:tuple((int(h[i:i+2],16)/255)**2.2 for i in (0,2,4))
def clear(): bpy.ops.wm.read_factory_settings(use_empty=True)
_M={}
def mat(name,h,rough=.85,emit=0):
    m=bpy.data.materials.get(name)
    if m: return m
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*hx(h),1); b.inputs['Roughness'].default_value=rough
    if emit: b.inputs['Emission Color'].default_value=(*hx(h),1); b.inputs['Emission Strength'].default_value=emit
    return m
def join_all(name):
    ms=[o for o in bpy.data.objects if o.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in ms: o.select_set(True)
    bpy.context.view_layer.objects.active=ms[0]
    if len(ms)>1: bpy.ops.object.join()
    o=bpy.context.object; bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM'); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for x in list(bpy.data.objects):
        if x!=o: bpy.data.objects.remove(x)
    o.name=name; return o
def snowtop(o,thr=.5,only=None):
    sn=mat('Snow','F4F8FF',.9); me=o.data
    if sn.name not in [m.name for m in me.materials]: me.materials.append(sn)
    si=[m.name for m in me.materials].index(sn.name)
    for p in me.polygons:
        if p.normal.z>thr and (only is None or me.materials[p.material_index].name in only): p.material_index=si
def finish(o,height=None,scale=None,ground=True):
    if height: s=height/o.dimensions.z
    else: s=scale or 1
    o.scale=(s,s,s); bpy.ops.object.transform_apply(scale=True)
    if ground:
        zmin=min(v.co.z for v in o.data.vertices); 
        for v in o.data.vertices: v.co.z-=zmin
    return o
def save(name):
    bpy.ops.export_scene.gltf(filepath=f'{OUT}/{name}.glb',export_format='GLB',export_apply=True,export_yup=True)
STATS={}
def imp(path,name,**kw):
    clear(); bpy.ops.import_scene.gltf(filepath=path); o=join_all(name)
    if kw.get('recolor'):
        for m in o.data.materials:
            if m.name.split('.')[0] in kw['recolor']: m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*hx(kw['recolor'][m.name.split('.')[0]]),1)
    finish(o,kw.get('height'),kw.get('scale'))
    if kw.get('snow') is not None: snowtop(o,kw['snow'],kw.get('only'))
    save(name); STATS[name]=dict(src=path.replace(RAW+'/',''),dims=[round(x,2) for x in o.dimensions])
# ---- Kenney Nature Kit (snow-dusted)
for n,h in [('tree_pineDefaultA',8),('tree_pineDefaultB',7),('tree_pineRoundA',6),('tree_pineRoundC',6.5),('tree_pineTallA',10),('tree_pineTallB',9),('tree_pineSmallA',3.5)]:
    imp(N+n+'.glb','pine_'+n.split('_')[1],height=h,snow=.45,only=['leafsDark'],recolor={'leafsDark':'2E5E4E'})
for n,h in [('rock_largeA',1.6),('rock_largeC',2.2),('stone_largeA',1.4),('cliff_large_rock',9)]:
    imp(N+n+'.glb',n,height=h,snow=.55,recolor={'grass':'F4F8FF','dirt':'7B7F8C','stone':'8A8F9C'})
imp(N+'fence_simple.glb','fence_wood',scale=2.4)
imp(N+'log_stack.glb','log_stack',scale=2.0,snow=.6)
# ---- Kenney Holiday Kit
for n,s in [('tree-snow-a',4.5),('tree-snow-b',4.5),('tree-snow-c',4.5),('rocks-large',1.2),('snow-pile',2.5),('snowman',1.6),('lantern',1.4),('bench',1.6),('sled',1.5)]:
    imp(H+n+'.glb','h_'+n.replace('-','_'),scale=s)
# ---- Quaternius Stylized Nature MegaKit (textured)
imp(QN+'Rock_Medium_1.gltf','q_rock_medium1',height=2.0,snow=.6)
imp(QN+'Pine_3.gltf','q_pine3',height=9)
# ---- custom props (made here, CC0)
def box(bm,c,s,rz=0):
    r=bmesh.ops.create_cube(bm,size=1)
    for v in r['verts']: v.co=M.Rotation(rz,4,'Z')@V((v.co.x*s[0],v.co.y*s[1],v.co.z*s[2]))+V(c)
    return r['verts']
def cyl(bm,c,r,d,seg=10,axis='Z',r2=None):
    res=bmesh.ops.create_cone(bm,cap_ends=True,segments=seg,radius1=r,radius2=r2 if r2 is not None else r,depth=d)
    rot={'Z':M(),'X':M.Rotation(R(90),4,'Y'),'Y':M.Rotation(R(90),4,'X')}[axis]
    for v in res['verts']: v.co=rot@v.co+V(c)
    return res['verts']
def build(name,parts):
    """parts: list of (matname,hex,fn(bm))"""
    clear(); me=bpy.data.meshes.new(name); bm=bmesh.new(); mats=[]
    for mn,hh,fn in parts:
        if mn not in mats: mats.append(mn)
        before=set(bm.faces); fn(bm); idx=mats.index(mn)
        for f in bm.faces:
            if f not in before: f.material_index=idx
    bm.to_mesh(me); bm.free(); o=bpy.data.objects.new(name,me); bpy.context.scene.collection.objects.link(o)
    for mn in mats: me.materials.append(mat(mn,dict((a,b) for a,b,_ in parts)[mn], emit=2 if mn=='Window' else 0))
    bpy.context.view_layer.objects.active=o; save(name); STATS[name]=dict(src='custom (Powder Rush, CC0)',dims=[round(x,2) for x in o.dimensions])
def roof(bm,w,d,h,z,over=.4,thick=.25,lift=0):
    # gable along X (ridge along X)
    x=w/2+over; y=d/2+over
    vs=[V((-x,-y,z)),V((x,-y,z)),V((x,0,z+h)),V((-x,0,z+h)),V((-x,y,z)),V((x,y,z))]
    for side in (1,-1):
        a=[V((-x,-y*side,z+lift)),V((x,-y*side,z+lift)),V((x,0,z+h+lift)),V((-x,0,z+h+lift))]
        b=[p+V((0,0,thick)) for p in a]
        va=[bm.verts.new(p) for p in a]; vb=[bm.verts.new(p) for p in b]
        bm.faces.new(vb if side==1 else vb[::-1]); bm.faces.new(va[::-1] if side==1 else va)
        for i in range(4):
            j=(i+1)%4; f=[va[i],va[j],vb[j],vb[i]]; bm.faces.new(f if side==1 else f[::-1])
def gable(bm,w,d,h,z):
    for s in (1,-1):
        vs=[bm.verts.new(V((s*w/2,-d/2,z))),bm.verts.new(V((s*w/2,d/2,z))),bm.verts.new(V((s*w/2,0,z+h)))]
        bm.faces.new(vs if s==1 else vs[::-1])
W_,D_,Hh=7,5.5,3.2
build('chalet',[('Wood','8B5A3C',lambda bm:(box(bm,(0,0,Hh/2),(W_,D_,Hh)),gable(bm,W_,D_,2.2,Hh))),
                ('WoodDark','5A3A28',lambda bm:(box(bm,(0,-D_/2-.02,1.05),(1.1,.1,2.1)),box(bm,(0,0,.15),(W_+.2,D_+.2,.3)))),
                ('Window','FFD58A',lambda bm:[box(bm,(x,-D_/2-.03,1.8),(1.0,.08,.9)) for x in (-2.2,2.2)]+[box(bm,(W_/2+.03,y,1.8),(.08,1.0,.9)) for y in (-1.2,1.2)]),
                ('Roof','7A2E2E',lambda bm:roof(bm,W_,D_,2.2,Hh-.05)),
                ('Snow','F4F8FF',lambda bm:(roof(bm,W_,D_,2.2,Hh+.2,over=.45,thick=.22),box(bm,(2,1.3,Hh+2.3),(.7,.7,.15)))),
                ('Stone','8A8F9C',lambda bm:box(bm,(2,1.3,Hh+1.4),(.6,.6,1.8)))])
build('lift_pylon',[('Steel','9AA3AE',lambda bm:(cyl(bm,(0,0,5),.28,10,8,r2=.18),box(bm,(0,0,10.1),(4.6,.35,.35)))),
                    ('LiftAccent','E4572E',lambda bm:[cyl(bm,(s*2.1,0,9.75),.32,.18,12,'Y') for s in (1,-1)]),
                    ('Concrete','B9BDC4',lambda bm:box(bm,(0,0,.3),(1.2,1.2,.6)))])
build('lift_chair',[('Steel','9AA3AE',lambda bm:(cyl(bm,(0,0,-1.1),.04,2.2,6),box(bm,(0,0,-2.2),(1.9,.08,.08)),[box(bm,(s*.95,.25,-2.45),(.06,.06,.5)) for s in (1,-1)])),
                    ('Seat','2F86A6',lambda bm:(box(bm,(0,.3,-2.65),(1.9,.55,.1)),box(bm,(0,.58,-2.3),(1.9,.08,.6)))),
                    ('LiftAccent','E4572E',lambda bm:box(bm,(0,0,-.05),(.3,.3,.25)))])
def tube(bm,a,b,r,seg=10):
    a=V(a);b=V(b);d=b-a; res=bmesh.ops.create_cone(bm,cap_ends=True,segments=seg,radius1=r,radius2=r,depth=d.length)
    q=d.normalized().to_track_quat('Z','Y').to_matrix().to_4x4()
    for v in res['verts']: v.co=M.Translation((a+b)/2)@q@v.co
build('rail_flat',[('Rail','C9CED6',lambda bm:tube(bm,(-3.5,0,.75),(3.5,0,.75),.055,12)),
                   ('RailPost','1E2A4F',lambda bm:[(tube(bm,(x,0,0),(x,0,.72),.05,8),box(bm,(x,0,.02),(.5,.5,.04))) for x in (-3,0,3)])])
build('rail_down',[('Rail','C9CED6',lambda bm:(tube(bm,(-4,0,1.4),(-1.5,0,1.4),.055,12),tube(bm,(-1.5,0,1.4),(4,0,.5),.055,12))),
                   ('RailPost','1E2A4F',lambda bm:[tube(bm,(x,0,0),(x,0,z-.03),.05,8) for x,z in ((-3.5,1.4),(-1.5,1.4),(1.25,.95),(3.6,.57))])])
build('funbox',[('BoxTop','2F86A6',lambda bm:box(bm,(0,0,.6),(6,.6,.05))),('BoxSide','F07A1A',lambda bm:box(bm,(0,0,.29),(5.9,.55,.58)))])
def kicker(bm,L=5,Wd=4,Hk=1.6,n=8):
    prof=[]
    for i in range(n+1):
        t=i/n; x=-L/2+L*t; z=Hk*(1-math.cos(t*math.pi/2))**1.0; prof.append((x,z))
    prof=[(-L/2,0)]+prof[1:]+[(L/2,0)]
    vl=[bm.verts.new((x,-Wd/2,z)) for x,z in prof]; vr=[bm.verts.new((x,Wd/2,z)) for x,z in prof]
    bm.faces.new(vl[::-1]); bm.faces.new(vr)
    for i in range(len(prof)-1):
        bm.faces.new([vl[i],vl[i+1],vr[i+1],vr[i]])
    bm.faces.new([vl[-1],vl[0],vr[0],vr[-1]])
build('kicker',[('Snow','F4F8FF',kicker),('LiftAccent','2F86A6',lambda bm:box(bm,(2.5,0,1.6),(.06,4.02,.06)))])
build('slalom_gate',[('Pole','EDE6D6',lambda bm:[tube(bm,(x,0,0),(x,0,1.9),.03,6) for x in (-.6,.6)]),('Flag','F07A1A',lambda bm:box(bm,(0,0,1.5),(1.2,.02,.7)))])
build('safety_net',[('Pole','EDE6D6',lambda bm:[tube(bm,(x,0,0),(x,0,1.3),.035,6) for x in (-2,0,2)]),
                    ('Net','F06A1A',lambda bm:[box(bm,(0,0,z),(4,.03,.12)) for z in (.35,.75,1.15)])])
build('start_arch',[('Steel','1E2A4F',lambda bm:[tube(bm,(x,0,0),(x,0,4.2),.15,8) for x in (-4,4)]),
                    ('Banner','F07A1A',lambda bm:box(bm,(0,0,3.8),(8.3,.12,.9))),('LiftAccent','2F86A6',lambda bm:box(bm,(0,-.07,3.8),(7.6,.02,.25)))])
build('trail_sign',[('Pole','5A3A28',lambda bm:tube(bm,(0,0,0),(0,0,1.9),.05,6)),
                    ('SignBlue','2F86A6',lambda bm:cyl(bm,(0,-.07,1.75),.28,.04,16,'Y'))])
json.dump(STATS,open('/workspace/powder-assets/out/decor_stats.json','w'),indent=1)
