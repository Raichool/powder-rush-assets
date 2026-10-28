import bpy,random,math,sys
from mathutils import Vector as V
R=math.radians; D='/workspace/powder-assets/out/decor_raw/'; P='/workspace/powder-assets/raw/polyhaven/'
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
cache={}
def put(n,x,y,rz=0,s=1):
    if n not in cache:
        bpy.ops.import_scene.gltf(filepath=D+n+'.glb'); o=bpy.context.selected_objects[0]; cache[n]=o
    else:
        o=cache[n].copy(); sc.collection.objects.link(o)
    o.location=(x,y,0); o.rotation_euler=(0,0,rz); o.scale=(s,s,s); return o
random.seed(3)
bpy.ops.mesh.primitive_plane_add(size=400); g=bpy.context.object
m=bpy.data.materials.new('snow'); m.use_nodes=True; nt=m.node_tree; b=nt.nodes['Principled BSDF']
t=nt.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(P+'snow_02_diff_1k.jpg')
mp=nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value=(60,60,60); tc=nt.nodes.new('ShaderNodeTexCoord')
nt.links.new(tc.outputs['UV'],mp.inputs[0]); nt.links.new(mp.outputs[0],t.inputs[0]); nt.links.new(t.outputs[0],b.inputs['Base Color']); g.data.materials.append(m)
pines=['pine_pineDefaultA','pine_pineDefaultB','pine_pineRoundA','pine_pineRoundC','pine_pineTallA','pine_pineTallB','h_tree_snow_a','h_tree_snow_b','h_tree_snow_c']
for i in range(140):
    x=random.uniform(-70,70); y=random.uniform(8,140)
    if abs(x)<12 and y<60: continue
    put(random.choice(pines),x,y,random.uniform(0,6.28),random.uniform(.8,1.3))
for i in range(14): put(random.choice(['rock_largeA','rock_largeC','stone_largeA','q_rock_medium1']),random.uniform(-40,40),random.uniform(10,80),random.uniform(0,6),random.uniform(.8,1.5))

put('chalet',-16,28,R(-20)); put('h_snowman',-10,22,R(30)); put('log_stack',-21,24,R(70)); put('h_lantern',-11,25)
for i in range(6): put('lift_pylon',20,10+i*22)
for i in range(12): c=put('lift_chair',17.9 if i%2 else 22.1,12+i*9.5); c.location.z=10-0.05
put('start_arch',0,60); put('kicker',2,32,R(90),1.4); put('rail_flat',-4,20,R(90)); put('funbox',5,18,R(90))
for i in range(5): put('slalom_gate',(-1)**i*6,40+i*4)
for i in range(6): put('safety_net',-11,10+i*4.2,R(90))
put('trail_sign',9,14); put('h_bench',-12,30,R(160))
bpy.ops.import_scene.gltf(filepath='/workspace/powder-assets/out/rider_v3_raw.glb')
arm=[o for o in bpy.context.selected_objects if o.type=='ARMATURE'][0]
arm.location=(0,10,0); arm.rotation_euler=(0,0,R(-60))
if arm.animation_data is None: arm.animation_data_create()
act=bpy.data.actions.get('ride') or [a for a in bpy.data.actions if 'ride' in a.name][0]; arm.animation_data.action=act; sc.frame_set(5)
w=sc.world=bpy.data.worlds.new('w'); w.use_nodes=True; e=w.node_tree.nodes.new('ShaderNodeTexEnvironment'); e.image=bpy.data.images.load(P+'snow_field_2_puresky_1k.hdr')
w.node_tree.links.new(e.outputs[0],w.node_tree.nodes['Background'].inputs[0])
bpy.ops.object.light_add(type='SUN',rotation=(R(50),0,R(-140))); bpy.context.object.data.energy=3.5
bpy.ops.object.camera_add(location=(4,0.5,2.6)); cam=bpy.context.object; sc.camera=cam; cam.data.lens=28
d=V((0,22,1.5))-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.use_denoising=True; sc.render.resolution_x=1600; sc.render.resolution_y=900
sc.view_settings.view_transform='AgX'; sc.render.filepath='/workspace/powder-assets/renders/scenery.png'; bpy.ops.render.render(write_still=True)
