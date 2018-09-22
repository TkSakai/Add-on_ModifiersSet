# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

bl_info = {
    "name": "Modifiers Set",
    "author": "TkSakai",
    "version": (0, 1),
    "blender": (2, 79, 0),
    "location": "PROPERTIES > Modifiers > Modifier Set",
    "description": "Make modifiers set",
    "warning": "Version difference between files could cause unexpected behaviour",
    "wiki_url": "https://github.com/TkSakai/Add-on_ModifiersSet",
    "category": "Object",
}

import bpy

### UI ###
prefix = "DATAHOLDER_mh_"

class ModifiersSetList(bpy.types.UIList):
    
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        layout.prop(item,"name",text="",emboss=False)


class DATA_PT_ModifiersSet(bpy.types.Panel):
    bl_label = "Modifier Set"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    #bl_options = {'HIDE_HEADER'}
    
    def draw(self,context):
        lo = self.layout
        clm = lo.column(align = True)
        row = clm.row(align = True)
        row.operator("modifierset.add",icon="ZOOMIN")
        row.operator("modifierset.remove",icon = "X")
        clm.operator("modifierset.apply",icon = "MODIFIER")


        clm.template_list("ModifiersSetList","",context.scene,"modifiersSet",context.scene,"modifiersSetIndex",rows=3)
        
        row = clm.row(align = True)
        row.operator("modifierset.save",icon="SAVE_AS") 
        row.operator("modifierset.load",icon="FILESEL")
        
       
### Operator ###      


class AddModifierSet(bpy.types.Operator):
    bl_idname = "modifierset.add"
    bl_label = "Add"
    bl_description = "Create Modifiers Set from Modifiers(undo-able)"    
    bl_options = {"REGISTER","UNDO"}
    

    @classmethod
    def poll(self,context):        
        return len([mod for ob in context.selected_objects for mod in ob.modifiers])

    
    def execute(self,context):
        return {"FINISHED"}
    
    def invoke(self,context,event):
        
        #print ("AddModifierSet")
        
        for ob in context.selected_objects:            
            
            if len(ob.modifiers) == 0:
                continue
            
            copiedOb = ob.copy()
            
            if bpy.data.meshes.find("mh_empty_mesh") == -1:
                bpy.data.meshes.new(name="mh_empty_mesh")
            copiedOb.data = bpy.data.meshes["mh_empty_mesh"]
            
            
            modSetName = "-".join([mod.name for mod in copiedOb.modifiers])
            modSetName = "{}__[{}]".format(ob.name,modSetName)
            copiedOb.name = "{}_{}".format(prefix,modSetName)
            AddToSceneModifiersSet(copiedOb,modSetName,context)

        return self.execute(context)
    
class RemoveModifierSet(bpy.types.Operator):
    bl_idname = "modifierset.remove"
    bl_label = "Remove"
    bl_description = "Remove Modifiers Set (undo-able) "  
    bl_options = {"REGISTER","UNDO"}
    
    @classmethod
    def poll(self,context):
        return len(context.scene.modifiersSet)
      
    def execute(self,context):
        return {"FINISHED"}
    
    def invoke(self,context,event):
        
        try:
            holderName = context.scene.modifiersSet[context.scene.modifiersSetIndex].holderName        
            context.scene.modifiersSet.remove(context.scene.modifiersSetIndex)
            
            bpy.data.objects[holderName].use_fake_user = False
            bpy.data.objects[holderName].isModifiersHolder = False
            
 
        
        except IndexError:
            pass
                        
        return self.execute(context)    

class ApplyModifierSet(bpy.types.Operator):
    bl_idname = "modifierset.apply"
    bl_label = "Apply"
    bl_description = "Apply Selected Modifiers Set (undo-able)"
    bl_options = {"REGISTER","UNDO"}
    
    @classmethod    
    def poll(self,context):
        return len(context.scene.modifiersSet)
    
    def execute(self,context):
        return {"FINISHED"}
    
    def invoke(self,context,event):
        
        try:
            srcName = context.scene.modifiersSet[context.scene.modifiersSetIndex].holderName
            srcOb = bpy.data.objects[srcName]
            
            for ob in context.selected_objects:
                SetModProperty(ob,GetModProperty(srcOb))
            
        except IndexError:
            pass
        
        return self.execute(context)
    

class LoadModifierSet(bpy.types.Operator):
    bl_idname = "modifierset.load"
    bl_label = "Load From Blend File"
    bl_description = "Load Modifiers Set from .blend File"
    
    filepath = bpy.props.StringProperty(subtype = "FILE_PATH")
    
    def execute(self,context):
        
        print ("Loading from File : {}".format(self.filepath))
        
        with bpy.data.libraries.load(self.filepath) as (data_from,data_to):
            data_to.objects = [ob for ob in data_from.objects if ob.startswith(prefix)]
            
        for ob in data_to.objects:
            modSetName = ob.modifiersSetName
            AddToSceneModifiersSet(ob,modSetName,context)
                    
        return {"FINISHED"}
    
    def invoke(self,context,event):
        context.window_manager.fileselect_add(self)
        
        return {"RUNNING_MODAL"}

class SaveModifierSet(bpy.types.Operator):
    bl_idname = "modifierset.save"
    bl_label = "Save as Blend File"
    bl_description = "Save Modifiers Set as a .blend File\n(may unavailable before 2.78.\nIf so use 'Save Copy' in File menu instead)"
    
    filepath = bpy.props.StringProperty(subtype = "FILE_PATH")
    
    @classmethod
    def poll(self,context):
        return len(context.scene.modifiersSet) and hasattr(bpy.data.libraries,"write")
    
    def execute(self,context):
        
        print ("Saving to File : {}".format(self.filepath))
        
        holderObjects = {ob for ob in bpy.data.objects if ob.name.startswith(prefix) and ob.isModifiersHolder}
        
        bpy.data.libraries.write(self.filepath,holderObjects)
                    
        return {"FINISHED"}
    
    def invoke(self,context,event):
        context.window_manager.fileselect_add(self)
        
        return {"RUNNING_MODAL"}
        
    
### FUNCTIONS ###

def AddToSceneModifiersSet(ob,name,context):
    
    #print ("AddToSceneModifiersSet")
    ob.use_fake_user = True
    ob.isModifiersHolder = True
    
    modSet = context.scene.modifiersSet.add()
    
    modSet.name = name
    modSet.holderName = ob.name
    
    ob.modifiersSetName = modSet.name
    
    context.scene.modifiersSetIndex = len(context.scene.modifiersSet)-1
    
    

def GetModProperty(ob):    
    ModPropList =[]
    for mod in ob.modifiers:
        innerDic = {}
        props = dir(mod)
        for prop in props:
            innerDic[prop] = getattr(mod,prop)
        ModPropList.append(innerDic)
    
    return ModPropList

def SetModProperty(ob,ModPropList):

    ob.modifiers.clear()

    for props in ModPropList:
        mod = ob.modifiers.new(type=props["type"],name=props["name"])
        
        for p in dir(mod):
            try:
                setattr(mod,p,props[p])
            except :
                pass    


### PROPERTIES ###

def nameChangeCallBack(self,context):
    
    #print ("nameChangeCallback")
    scn = context.scene
    idx = scn.modifiersSetIndex
    
    modSet = scn.modifiersSet[idx]
    holderName = modSet.holderName
    
    #print ("{}-{}".format(modSet,holderName))
    

    if holderName == "ErrholderName":
        return

    
    bpy.data.objects[holderName].modifiersSetName = modSet.name
    


class ModifiersSet(bpy.types.PropertyGroup):
    
    name = bpy.props.StringProperty(name = "name",default = "ErrName",update=nameChangeCallBack)         
    holderName = bpy.props.StringProperty(name ="holderName",default="ErrholderName")

    

clss = [SaveModifierSet,LoadModifierSet,RemoveModifierSet,AddModifierSet,ApplyModifierSet,DATA_PT_ModifiersSet,ModifiersSet,ModifiersSetList]


### REGISTER ###

def draw(self,context):
    lo = self.layout

def register():
    for cls in clss:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.modifiersSet = bpy.props.CollectionProperty(type=ModifiersSet)
   
    bpy.types.Scene.modifiersSetIndex = bpy.props.IntProperty(default = 0)    
    bpy.types.Object.isModifiersHolder = bpy.props.BoolProperty(default = False)    
    bpy.types.Object.modifiersSetName = bpy.props.StringProperty()
    
    bpy.types.DATA_PT_modifiers.prepend(draw)
    
def unregister():
    for cls in clss:
        bpy.utils.unregister_class(cls)
        
if __name__ == "__main__":   
    register()    