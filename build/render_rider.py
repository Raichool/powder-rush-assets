import bpy,math,sys
from mathutils import Vector as V
args=sys.argv[sys.argv.index('--')+1:]; mode=args[0]
bpy.ops.wm.open_mainfile(filepath='/workspace/powder-assets/build/rider_v3.blend')
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=16; sc.cycles.use_denoising=True
sc.render.resolution_x=int(args[1]); sc.render.resolution_y=int(args[2]); sc.view_settings.view_transform='Standard'
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(.72,.78,.86,1); w.node_tree.nodes['Background'].inputs[1].default_value=1.0
sun=bpy.data.objects.new('sun',bpy.data.lights.new('sun','SUN')); sc.collection.objects.link(sun); sun.data.energy=3.5; sun.rotation_euler=(math.radians(50),0,math.radians(-30))
# snow ground
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,-.02)); g=bpy.context.object; m=bpy.data.materials.new('snow'); m.use_nodes=True; m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.93,.95,1,1); g.data.materials.append(m)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=50
arm=bpy.data.objects['Rider']
def shot(action,frame,ang,path,dist=4.2,h=1.0,tz=.75):
    arm.animation_data.action=bpy.data.actions[action]; sc.frame_set(frame)
    a=math.radians(ang); cam.location=(dist*math.sin(a),-dist*math.cos(a),h)
    d=V((0,0,tz))-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=path; bpy.ops.render.render(write_still=True)
if mode=='views':
    for act,fr,ang,n in [('idle',0,0,'front'),('idle',0,-35,'34'),('idle',0,180,'back'),('ride',0,-35,'ride34'),('ride',0,-90,'rideside')]:
        shot(act,fr,ang,f'/tmp/rv_{n}.png')
elif mode=='anims':
    for act in args[3].split(','):
        n=int(args[4]) if len(args)>4 else 0
        a=bpy.data.actions[act]; f=int(a.frame_range[1]*float(args[5])) if len(args)>5 else 0
        shot(act,f,-35,f'/tmp/ra_{act}.png',dist=5.2,h=1.6,tz=.8)
if mode=='sheet':
    F={'idle':0,'ride':0,'carve_L':0,'carve_R':0,'jump':.4,'air':0,'grab_indy':.9,'grab_melon':.9,'grab_method':.9,'spin360_L':.35,'flip':.4,'grind':.25,'land':.3,'fall':.95,'celebrate':.25,'spin360_R':.35}
    for act,fr in F.items():
        a=bpy.data.actions[act]; f=round(a.frame_range[1]*fr)
        shot(act,f,-30,f'/tmp/ra_{act}.png',dist=5.0,h=1.5,tz=.75)
