import bpy, bmesh, math, sys, json
from mathutils import Vector as V, Matrix as M, Euler as E, Quaternion as Q
from mathutils.bvhtree import BVHTree
R=math.radians
OUT='/workspace/powder-assets/out'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath="/workspace/powder-assets/raw/ubc/Universal Base Characters[Standard]/Base Characters/Godot - UE/Superhero_Male_FullBody.gltf")
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]; arm.name='Rider'
body=bpy.data.objects['SuperHero_Male']; body.name='RiderBody'
eyes=bpy.data.objects['Eyes']; ez=sum(((eyes.matrix_world@v.co).z for v in eyes.data.vertices))/len(eyes.data.vertices)
for o in list(bpy.data.objects):
    if o not in (arm,body): bpy.data.objects.remove(o)
print('eye z',ez)
# ---------- materials
def mat(name,col,rough=.8,metal=0,img=None):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*[c**2.2 for c in col],1); b.inputs['Roughness'].default_value=rough; b.inputs['Metallic'].default_value=metal
    if img:
        t=m.node_tree.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(img); m.node_tree.links.new(t.outputs[0],b.inputs['Base Color'])
    return m
hx=lambda h:tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
PAL={'Jacket':'F07A1A','Accent':'2F86A6','Pants':'1E2A4F','Gloves':'2C7FA0','Boots':'3A8FB0','Sole':'EDE6D6','Mask':'1B2547','Beanie':'EDE6D6','Strap':'1E2A4F'}
MATS={k:mat(k,hx(v)) for k,v in PAL.items()}
MATS['Lens']=mat('Lens',hx('4FB3D9'),.15,.6)
MATS['Board']=mat('Board',(1,1,1),.5,img='/workspace/powder-assets/build/board_tex.png')
# ---------- regions
me=body.data; vg={g.index:g.name for g in body.vertex_groups}
HEM=0.84
bm=bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-4)
for zc in (HEM,0.20,0.035):
    bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=(0,0,zc),plane_no=(0,0,1))
bm.to_mesh(me); bm.free(); me.update()
def region(v):
    w=max(v.groups,key=lambda g:g.weight); n=vg[w.group]; z=v.co.z
    if n=='Head': return 'Mask'
    if n.startswith(('neck','spine','clavicle','upperarm','lowerarm')): return 'Jacket'
    if n.startswith(('hand','index','middle','ring','pinky','thumb')): return 'Gloves'
    if n.startswith(('pelvis','thigh')): return 'Jacket' if z>HEM else 'Pants'
    if n.startswith('calf'): return 'Pants' if z>0.20 else 'Boots'
    if n.startswith(('foot','ball')): return 'Sole' if z<0.035 else 'Boots'
    return 'Pants'
vr=[region(v) for v in me.vertices]
body.data.materials.clear()
order=['Jacket','Pants','Gloves','Boots','Sole','Mask']
for k in order: me.materials.append(MATS[k])
for p in me.polygons:
    rs=[vr[i] for i in p.vertices]; r=max(set(rs),key=rs.count)
    z=p.center.z
    if r in('Jacket','Pants') and z<1.0 and not any(vg[max(me.vertices[i].groups,key=lambda g:g.weight).group].startswith(('hand','index','middle','ring','pinky','thumb','lowerarm')) for i in p.vertices): r='Jacket' if z>HEM else 'Pants'
    if r in('Pants','Boots','Sole') and z<0.6: r='Pants' if z>0.20 else ('Boots' if z>0.035 else 'Sole')
    p.material_index=order.index(r)
# smooth away muscle definition on clothed areas
vmat=[set() for _ in me.vertices]
for p in me.polygons:
    for i in p.vertices: vmat[i].add(order[p.material_index])
nb0=[[] for _ in me.vertices]
for e in me.edges: a,b=e.vertices; nb0[a].append(b); nb0[b].append(a)
for it in range(6):
    co=[v.co.copy() for v in me.vertices]
    for v in me.vertices:
        if vmat[v.index]<= {'Jacket','Pants'} and nb0[v.index] and len(nb0[v.index])>=4:
            avg=sum((co[j] for j in nb0[v.index]),V())/len(nb0[v.index]); v.co=co[v.index].lerp(avg,.5)
me.update()
OFF={'Jacket':.028,'Pants':.03,'Gloves':.01,'Boots':.018,'Sole':.018,'Mask':.004}
off=[0.0]*len(me.vertices); cnt=[0]*len(me.vertices)
for p in me.polygons:
    o=OFF[order[p.material_index]]
    if order[p.material_index]=='Pants': o+=.035*max(0,1-p.center.z/0.8)
    if order[p.material_index]=='Jacket' and p.center.z<1.0: o+=.012
    for i in p.vertices: off[i]+=o; cnt[i]+=1
off=[off[i]/max(cnt[i],1) for i in range(len(off))]
nb=[[] for _ in me.vertices]
for e in me.edges: a,b=e.vertices; nb[a].append(b); nb[b].append(a)
for it in range(4): off=[(off[i]+sum(off[j] for j in nb[i]))/(1+len(nb[i])) for i in range(len(off))]
# weld-aware normals: average normals of co-located verts (UV seams)
from collections import defaultdict
pos=defaultdict(list)
for v in me.vertices: pos[tuple(round(c,4) for c in v.co)].append(v.index)
nrm=[v.normal.copy() for v in me.vertices]
for k,ids in pos.items():
    n=sum((me.vertices[i].normal for i in ids),V()).normalized(); oo=max(off[i] for i in ids)
    for i in ids: nrm[i]=n; off[i]=oo
for v in me.vertices: v.co+=nrm[v.index]*off[v.index]
me.update()
# ---------- accessory helpers
def add_obj(name,bm,matname,weights):
    m=bpy.data.meshes.new(name); bm.to_mesh(m); bm.free(); o=bpy.data.objects.new(name,m); bpy.context.scene.collection.objects.link(o)
    if isinstance(matname,str): m.materials.append(MATS[matname])
    else:
        for k in matname: m.materials.append(MATS[k])
    for bn,wt in weights:
        g=o.vertex_groups.new(name=bn); g.add(list(range(len(m.vertices))),wt,'REPLACE')
    o.parent=arm; mo=o.modifiers.new('Armature','ARMATURE'); mo.object=arm
    for p in m.polygons: p.use_smooth=True
    return o
bvh=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
def decal(name,cx,cz,w,h,dirn,bone,matn='Accent',nx=5,ny=3,lift=.005,axis='x'):
    bm=bmesh.new(); grid=[]
    for j in range(ny+1):
        row=[]
        for i in range(nx+1):
            u=cx+(i/nx-.5)*w; z=cz+(j/ny-.5)*h
            if axis=='x': org=V((u,-dirn*1.0,z)) ; d=V((0,dirn,0))
            else: org=V((u,-dirn*1.0,z)); d=V((0,dirn,0))
            hit,n,_,_=bvh.ray_cast(org,d)
            if hit is None: hit=org; n=-d
            row.append(bm.verts.new(hit+n*lift))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            q=[grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]]
            if dirn<0: q=q[::-1]
            bm.faces.new(q)
    return add_obj(name,bm,matn,[(bone,1)])
dec=[decal('ChestPocket',.085,1.36,.075,.055,1,'spine_03'),
     decal('Zip',-.03,1.24,.014,.22,1,'spine_02',nx=1,ny=5),
     decal('PocketL',.12,.95,.085,.095,1,'pelvis'),decal('PocketR',-.12,.95,.085,.095,1,'pelvis'),
     decal('ArmPatchL',.30,1.47,.06,.05,1,'upperarm_l'),decal('ArmPatchR',-.30,1.47,.06,.05,1,'upperarm_r'),
     decal('BackStripe',0,1.40,.30,.022,-1,'spine_03',nx=10,ny=1)]
# beanie (top half sphere) + cuff, goggles
hc=V((0,0.012,ez+0.01)); 
bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=18,v_segments=10,radius=.122)
for v in bm.verts: v.co=V((v.co.x,v.co.y*1.05,v.co.z*1.12))+hc
geom=bm.verts[:]+bm.edges[:]+bm.faces[:]
bmesh.ops.bisect_plane(bm,geom=geom,plane_co=hc+V((0,0,.04)),plane_no=(0,0,1),clear_inner=True)
add_obj('Beanie',bm,'Beanie',[('Head',1)])
def ring(r,h,zc,seg=18,a0=0,a1=2*math.pi,sy=1.05,yc=None,matn='Beanie',name='Ring',bone='Head',closed=True):
    bm=bmesh.new(); top=[];bot=[]; n=seg if closed else seg+1
    for i in range(n):
        a=a0+(a1-a0)*i/seg; x=math.sin(a)*r; y=-math.cos(a)*r*sy+(yc if yc is not None else hc.y)
        bot.append(bm.verts.new((x,y,zc-h/2))); top.append(bm.verts.new((x,y,zc+h/2)))
    for i in range(seg):
        j=(i+1)%n; bm.faces.new([bot[i],bot[j],top[j],top[i]])
    return add_obj(name,bm,matn,[(bone,1)])
ring(.128,.05,hc.z+.06,name='BeanieCuff')
ring(.126,.032,ez,name='GoggleStrap',matn='Strap')
ring(.134,.055,ez,seg=10,a0=-R(58),a1=R(58),closed=False,name='GoggleLens',matn='Lens')
# hood bunch + collar
bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=12,v_segments=8,radius=1)
for v in bm.verts: v.co=V((v.co.x*.13,v.co.y*.07+.11,v.co.z*.085+1.53))
add_obj('Hood',bm,'Jacket',[('spine_03',1)])
ring(.088,.07,1.56,seg=14,yc=.02,sy=1.0,matn='Jacket',name='Collar',bone='neck_01')
# ---------- board bone + board mesh
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='EDIT')
eb=arm.data.edit_bones.new('board'); eb.head=(0,0,0); eb.tail=(0.3,0,0); eb.parent=arm.data.edit_bones['root']; eb.use_deform=True
bpy.ops.object.mode_set(mode='OBJECT')
L,Wd,T=1.56,.28,.018
pts=[]
for i in range(16):  # nose semicircle-ish (ellipse)
    a=-math.pi/2+math.pi*i/15; pts.append((L/2-.16+math.cos(a)*.16, math.sin(a)*Wd/2))
for i in range(16):
    a=math.pi/2+math.pi*i/15; pts.append((-L/2+.16+math.cos(a)*.16, math.sin(a)*Wd/2))
def lift(x): ax=abs(x); return (ax-.60)**2*1.4 if ax>.60 else 0
bm=bmesh.new(); top=[bm.verts.new((x,y,lift(x))) for x,y in pts]; bot=[bm.verts.new((x,y,lift(x)-T)) for x,y in pts]
ft=bm.faces.new(top); fb=bm.faces.new(bot[::-1]); n=len(pts)
for i in range(n): j=(i+1)%n; bm.faces.new([bot[i],bot[j],top[j],top[i]])
bmesh.ops.triangulate(bm,faces=[ft,fb])
uv=bm.loops.layers.uv.new()
for f in bm.faces:
    for l in f.loops: l[uv].uv=(l.vert.co.x/L+.5, l.vert.co.y/Wd+.5)
bo=add_obj('Board',bm,'Board',[('board',1)])
for p in bo.data.polygons: p.use_smooth=False
# bindings: base plate + highback per foot
SX=.25
for s,ang in ((1,R(15)),(-1,R(-9))):
    bm=bmesh.new()
    bmesh.ops.create_cube(bm,size=1)
    for v in bm.verts: v.co=V((v.co.x*.12,v.co.y*.24,v.co.z*.012+.006))
    hb=bmesh.new()
    r=bmesh.ops.create_cube(bm,size=1)
    for v in r['verts']: v.co=V((v.co.x*.12,v.co.y*.018+.12,v.co.z*.15+.08))
    for v in bm.verts: v.co=M.Rotation(ang,4,'Z')@v.co+V((s*SX,0,0))
    add_obj('Binding'+('L' if s>0 else 'R'),bm,'Strap',[('board',1)])
# ---------- rig controls
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='POSE')
P=arm.pose.bones
for pb in P: pb.rotation_mode='QUATERNION'
upd=lambda: bpy.context.view_layer.update()
def empty(n):
    e=bpy.data.objects.new(n,None); bpy.context.scene.collection.objects.link(e); return e
REST={b.name:b.matrix_local.copy() for b in arm.data.bones}
footT={};kneeP={}
for s,side,ang in ((1,'l',R(15)),(-1,'r',R(-9))):
    fr=REST['foot_'+side]
    m=M.Translation((s*SX,0,0))@M.Rotation(ang,4,'Z')@M.Translation((-fr.translation.x,.02,0))@fr
    e=empty('FootT_'+side); e.parent=arm; e.parent_type='BONE'; e.parent_bone='board'; upd(); e.matrix_world=m
    k=empty('KneeP_'+side); k.parent=arm; k.parent_type='BONE'; k.parent_bone='board'; upd(); k.matrix_world=M.Translation((s*SX*0.9,-.9,.55))
    footT[side]=e; kneeP[side]=k
    c=P['calf_'+side].constraints.new('IK'); c.target=e; c.pole_target=k; c.chain_count=2
    c2=P['foot_'+side].constraints.new('COPY_ROTATION'); c2.target=e
handT={};elbP={}
for side in 'lr':
    h=empty('HandT_'+side); p=empty('ElbP_'+side); handT[side]=h; elbP[side]=p
    c=P['lowerarm_'+side].constraints.new('IK'); c.target=h; c.pole_target=p; c.chain_count=2
# finger curl axis detection
fingers=[n for n in P.keys() if n.split('_')[0] in('index','middle','ring','pinky','thumb') and 'leaf' not in n]
def tipz(n):
    upd(); return (arm.matrix_world@P[n].tail).z if True else 0
CURL={}
for side in 'lr':
    best=None
    for ax in ('X','Z'):
        for sg in (1,-1):
            P['index_02_'+side].rotation_quaternion=Q(V((1,0,0)) if ax=='X' else V((0,0,1)),sg*R(60)); upd()
            z=(P['index_03_'+side].tail).z
            if best is None or z<best[0]: best=(z,ax,sg)
            P['index_02_'+side].rotation_quaternion=Q()
    CURL[side]=best[1:]; print('curl',side,best)
def curl_fingers(amt=1.0):
    for n in fingers:
        side=n[-1]; ax,sg=CURL[side]; a=R(55 if not n.startswith('thumb') else 20)*amt
        if n.endswith('_01_'+side) and not n.startswith('thumb'): a*=.7
        P[n].rotation_quaternion=Q(V((1,0,0)) if ax=='X' else V((0,0,1)),sg*a)
# ---------- pose application
def about(pt,R3): return M.Translation(pt)@R3.to_4x4()@M.Translation(-pt)
def eul(e): return E((R(e[0]),R(e[1]),R(e[2])),'XYZ').to_matrix()
def apply(ps):
    """ps: dict with B (4x4 rig->world), pel (dx,dy,dz), pelr (deg xyz), spine (deg), head (deg), hl, hr (rig-space hand pos)"""
    B=ps['B']; Bq=B.to_3x3()
    for pb in P:
        if not pb.name.split('_')[0] in('index','middle','ring','pinky','thumb'): pb.matrix_basis=M()
    curl_fingers(ps.get('curl',1))
    upd()
    P['board'].matrix=B@REST['board']; upd()
    ph=REST['pelvis'].translation
    P['pelvis'].matrix=B@M.Translation(V(ps['pel']))@about(ph,eul(ps.get('pelr',(0,0,0))))@REST['pelvis']; upd()
    sp=ps.get('spine',(0,0,0)); 
    for n in ('spine_01','spine_02','spine_03'):
        cur=P[n].matrix.copy(); P[n].matrix=about(cur.translation,Bq@eul([x/3 for x in sp])@Bq.inverted())@cur; upd()
    hd=ps.get('head',(0,0,0))
    for n,f in (('neck_01',.4),('Head',.6)):
        cur=P[n].matrix.copy(); P[n].matrix=about(cur.translation,Bq@eul([x*f for x in hd])@Bq.inverted())@cur; upd()
    for side,s in (('l',1),('r',-1)):
        hp=B@V(ps['h'+side]); handT[side].location=hp
        sh=P['upperarm_'+side].head.copy()
        out=Bq@V((s,0,0)); back=Bq@V((0,1,0)); down=Bq@V((0,0,-1))
        elbP[side].location=(sh+hp)/2+out*.35+back*.25+down*.35
    upd()
def lerp(a,b,t): return [x+(y-x)*t for x,y in zip(a,b)]
def ease(t): t=max(0,min(1,t)); return t*t*(3-2*t)
def mix(p,q,t):
    o={}
    for k in p:
        if k=='B': continue
        o[k]=lerp(p[k],q[k],t) if isinstance(p[k],(list,tuple)) else p[k]+(q[k]-p[k])*t
    return o
def rigB(loc=(0,0,0),rot=(0,0,0),pivot=(0,0,.6)):
    return M.Translation(V(loc))@about(V(pivot),eul(rot))
RIDE=dict(pel=(0,.06,-.28),pelr=(0,0,22),spine=(18,0,8),head=(-12,0,38),hl=(.52,-.18,.86),hr=(-.40,.08,.74),curl=1)
STAND=dict(pel=(0,.02,-.07),pelr=(0,0,10),spine=(4,0,4),head=(0,0,25),hl=(.30,-.06,.86),hr=(-.30,.06,.86),curl=.8)
TUCK=dict(pel=(0,.05,-.40),pelr=(0,0,15),spine=(30,0,6),head=(-25,0,30),hl=(.38,-.30,.95),hr=(-.35,-.20,.90),curl=1)
def P_(base,**kw): d=dict(base); d.update(kw); return d
S=math.sin; TAU=2*math.pi
ANIMS={}
def anim(name,frames,loop=False):
    def deco(f): ANIMS[name]=(frames,f,loop); return f
    return deco
@anim('idle',40,True)
def _(t): return P_(STAND,pel=(0,.02,-.07-.01*S(TAU*t)),B=rigB())
@anim('ride',40,True)
def _(t): return P_(RIDE,pel=(0,.06,-.28-.02*S(TAU*t)),hl=(.52,-.18,.86+.03*S(TAU*t)),B=rigB())
@anim('carve_R',30,True)   # toeside: turns right when nose = travel dir (+X)
def _(t): return P_(RIDE,pel=(0,-.02,-.34-.015*S(TAU*t)),spine=(26,0,6),hl=(.42,-.40,.45),hr=(-.30,-.22,.60),B=rigB(rot=(20+2*S(TAU*t),0,0),pivot=(0,0,0)))
@anim('carve_L',30,True)   # heelside
def _(t): return P_(RIDE,pel=(0,.13,-.36-.015*S(TAU*t)),spine=(6,0,10),head=(-5,0,40),hl=(.45,.20,.72),hr=(-.22,.42,.36),B=rigB(rot=(-20-2*S(TAU*t),0,0),pivot=(0,0,0)))
@anim('jump',18)
def _(t):
    if t<.45: q=ease(t/.45); d=mix(RIDE,P_(RIDE,pel=(0,.08,-.45),spine=(32,0,8),hl=(.25,.15,.55),hr=(-.45,.25,.55)),q)
    else: q=ease((t-.45)/.55); d=mix(P_(RIDE,pel=(0,.08,-.45),spine=(32,0,8),hl=(.25,.15,.55),hr=(-.45,.25,.55)),P_(RIDE,pel=(0,.03,-.06),spine=(4,0,4),hl=(.45,-.15,1.55),hr=(-.40,-.05,1.45)),q)
    d['B']=rigB((0,0,.12*ease((t-.5)/.5))); return d
@anim('air',24,True)
def _(t): return P_(TUCK,hl=(.55,-.10,1.05+.05*S(TAU*t)),hr=(-.55,.05,1.0-.05*S(TAU*t)),B=rigB())
def grab(hold,tweak):
    def f(t):
        q=ease(t/.3); d=mix(TUCK,hold,q); w=.04*S(TAU*t)*ease(t/.3)
        tw=[a*q+w*30 for a in tweak]; d['B']=rigB(rot=tw,pivot=(0,0,.62)); return d
    return f
ANIMS['grab_indy']=(30,grab(P_(TUCK,spine=(40,0,0),pel=(0,.02,-.44),hr=(-.05,-.17,.03),hl=(.55,-.10,1.15),head=(-20,0,35)),(0,0,0)),False)
ANIMS['grab_melon']=(30,grab(P_(TUCK,spine=(14,0,18),pel=(0,.10,-.44),pelr=(0,0,30),hl=(.03,.17,.03),hr=(-.55,.05,1.15),head=(-10,0,40)),(0,0,0)),False)
ANIMS['grab_method']=(30,grab(P_(TUCK,spine=(-12,0,25),pel=(0,.10,-.40),pelr=(0,0,35),hl=(.05,.17,.03),hr=(-.5,.15,1.2),head=(-5,0,55)),(-38,0,8)),False)
def spin(sign):
    def f(t):
        d=P_(TUCK,spine=(26,0,6-14*sign*S(math.pi*t)),hl=(.30,-.25,1.0),hr=(-.28,-.25,.95))
        d['B']=rigB(rot=(0,0,sign*360*ease(t)),pivot=(0,0,0)); return d
    return f
ANIMS['spin360_L']=(30,spin(1),False); ANIMS['spin360_R']=(30,spin(-1),False)
@anim('flip',36)
def _(t): 
    d=P_(TUCK,pel=(0,.05,-.46),spine=(36,0,4),hl=(.15,-.22,.70),hr=(-.18,-.22,.68),head=(-10,0,20)); d['B']=rigB(rot=(-360*ease(t),0,0),pivot=(0,0,.55)); return d
@anim('grind',40,True)
def _(t): return P_(RIDE,pel=(0,.04,-.18),pelr=(0,0,8+4*S(TAU*t)),spine=(10,0,4+6*S(TAU*t)),hl=(.78,-.05,1.12+.08*S(TAU*t)),hr=(-.74,.05,1.08-.08*S(TAU*t)),head=(-8,0,45),B=rigB(rot=(4*S(TAU*t),0,0),pivot=(0,0,0)))
@anim('land',18)
def _(t):
    low=P_(RIDE,pel=(0,.07,-.48),spine=(34,0,8),hl=(.55,-.32,.62),hr=(-.40,-.15,.55))
    d=mix(low,RIDE,ease((t-.3)/.7)) if t>.3 else mix(TUCK,low,ease(t/.3)); d['B']=rigB(); return d
@anim('fall',45)
def _(t):
    q=ease(t/.45); b=.06*abs(S(math.pi*min(1,max(0,(t-.45)/.3))))
    d=P_(RIDE,pel=(0,.10,-.30),spine=(-15*q,0,10),head=(-20*q,0,30),hl=(.6,.15+.2*S(9*t),1.2+.2*S(11*t)),hr=(-.6,.2+.2*S(10*t),1.1+.2*S(8*t)),curl=.3)
    d['B']=rigB((0,0,b),rot=(-95*q,0,-20*q),pivot=(0,.14,0)); return d
@anim('celebrate',40,True)
def _(t):
    pump=.5+.5*S(2*TAU*t)
    return P_(STAND,pelr=(0,0,0),spine=(-6,0,0),head=(-18,0,0),hl=(.32,-.08,1.75+.12*pump),hr=(-.32,-.08,1.70+.12*(1-pump)),B=rigB((0,0,.03*pump)))
# ---------- calibrate pole angles on crouched pose
apply(P_(RIDE,B=rigB()))
for side in 'lr':
    for bn,pole in (('calf_'+side,kneeP[side]),('lowerarm_'+side,elbP[side])):
        c=P[bn].constraints[0]; best=None
        for a in range(-180,180,10):
            c.pole_angle=R(a); upd(); d=(P[bn].head-pole.matrix_world.translation).length
            if best is None or d<best[0]: best=(d,a)
        c.pole_angle=R(best[1]); print('pole',bn,best)
# ---------- bake
KEYB=[pb for pb in P if 'leaf' not in pb.name]
def basis(pb):
    if pb.parent is None: return pb.bone.matrix_local.inverted()@pb.matrix
    rel=pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local
    return (pb.parent.matrix@rel).inverted()@pb.matrix
baked={}
for name,(n,f,loop) in ANIMS.items():
    fr=[]
    for i in range(n+1):
        t=i/n
        apply(f(t)); fr.append({pb.name:basis(pb) for pb in KEYB})
    baked[name]=fr
# remove constraints & controls
for pb in P:
    for c in list(pb.constraints): pb.constraints.remove(c)
for o in list(bpy.data.objects):
    if o.type=='EMPTY': bpy.data.objects.remove(o)
arm.animation_data_create()
for name,fr in baked.items():
    act=bpy.data.actions.new(name); act.use_fake_user=True; arm.animation_data.action=act
    for i,d in enumerate(fr):
        for bn,mb in d.items():
            pb=P[bn]; loc,rot,_=mb.decompose(); pb.rotation_quaternion=rot
            pb.keyframe_insert('rotation_quaternion',frame=i)
            if bn in('pelvis','board','root'): pb.location=loc; pb.keyframe_insert('location',frame=i)
    # quaternion continuity
    for fc in act.fcurves: pass
arm.animation_data.action=bpy.data.actions['ride']
bpy.ops.object.mode_set(mode='OBJECT')
# stats
dg=bpy.context.evaluated_depsgraph_get(); tri=0
for o in bpy.data.objects:
    if o.type=='MESH':
        o.data.calc_loop_triangles(); tri+=len(o.data.loop_triangles)
print('TRIS',tri)
json.dump({'tris':tri,'anims':{k:v[0] for k,v in ANIMS.items()}},open(OUT+'/rider_stats.json','w'))
bpy.ops.wm.save_as_mainfile(filepath='/workspace/powder-assets/build/rider_v3.blend')
def export(path):
    bpy.ops.export_scene.gltf(filepath=path,export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',export_skins=True,export_morph=False,export_yup=True,export_force_sampling=True,export_frame_range=False,export_image_format='AUTO')
export(OUT+'/rider_v3_raw.glb')
VAR={'red':{'Jacket':'D8313B','Accent':'F2C14E','Pants':'2B2B2E','Gloves':'F2C14E','Boots':'2B2B2E','Beanie':'2B2B2E','Lens':'F2C14E'},
     'green':{'Jacket':'3FA34D','Accent':'F4F1DE','Pants':'3D405B','Gloves':'3D405B','Boots':'F4F1DE','Beanie':'E07A5F','Lens':'E07A5F'},
     'purple':{'Jacket':'7B4FC9','Accent':'45D3C7','Pants':'1C1C3A','Gloves':'45D3C7','Boots':'45D3C7','Beanie':'F7F7F7','Lens':'FF6FB5'}}
json.dump({'blue':PAL,**VAR},open(OUT+'/rider_palettes.json','w'),indent=1)
for vn,cols in VAR.items():
    for k,h in cols.items():
        MATS[k].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*[c**2.2 for c in hx(h)],1)
    export(OUT+f'/rider_v3_{vn}_raw.glb')
