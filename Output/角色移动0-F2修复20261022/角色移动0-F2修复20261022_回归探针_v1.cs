using System;
using System.IO;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

[InitializeOnLoad]
public static class RoleMove0F2Regression20261022
{
    const string Key = "RoleMove0F2Regression20261022";
    const string Dir = "D:/myspace/Git/this/Output/角色移动0-F2修复20261022/";
    static StringBuilder report = new StringBuilder();
    static int frame = -1, failures;
    static double started;
    static bool ran;
    static RoleMove0F2Regression20261022()
    {
        if (SessionState.GetBool(Key,false)) Install();
    }
    public static void Run()
    {
        SessionState.SetBool(Key,true);
        EditorSceneManager.OpenScene("Assets/Scenes/PersistanceScene.unity",OpenSceneMode.Single);
        EditorSceneManager.OpenScene("Assets/Scenes/01.Field.unity",OpenSceneMode.Additive);
        EditorSceneManager.OpenScene("Assets/Scenes/UI.unity",OpenSceneMode.Additive);
        EditorSceneManager.OpenScene("Assets/Scenes/Template.unity",OpenSceneMode.Additive);
        Install(); EditorApplication.isPlaying = true;
    }
    static void Install()
    {
        started=EditorApplication.timeSinceStartup;
        EditorApplication.update-=Tick; EditorApplication.update+=Tick;
    }
    static void Tick()
    {
        if (ran && !EditorApplication.isPlaying && !EditorApplication.isPlayingOrWillChangePlaymode)
        {
            SessionState.EraseBool(Key); EditorApplication.update-=Tick;
            File.WriteAllText(Dir+"角色移动0-F2修复20261022_退出请求.txt","exit="+(failures==0?0:1));
            EditorApplication.Exit(failures==0?0:1); return;
        }
        if (EditorApplication.timeSinceStartup-started>120)
        { SessionState.EraseBool(Key); File.WriteAllText(Dir+"角色移动0-F2修复20261022_超时.txt","TIMEOUT"); EditorApplication.Exit(2); return; }
        if (!EditorApplication.isPlaying || ran) return;
        Application.runInBackground=true; EditorApplication.QueuePlayerLoopUpdate();
        if(frame<0) { frame=Time.frameCount; return; }
        if(Time.frameCount<frame+10) return;
        ran=true;
        report.AppendLine("UTC="+DateTime.UtcNow.ToString("o")+" frame="+frame+"->"+Time.frameCount);
        try { Checks(); } catch(Exception ex) { failures++; report.AppendLine(ex.ToString()); }
        report.AppendLine("RESULT failures="+failures);
        File.WriteAllText(Dir+"角色移动0-F2修复20261022_回归结果_v1.txt",report.ToString());
        EditorApplication.isPlaying=false;
    }
    static void Check(string name,bool ok,string detail="")
    { if(!ok) failures++; report.AppendLine((ok?"PASS ":"FAIL ")+name+" "+detail); }
    static bool At(MetaObjectPreset p,Vector2Int cell)
    {
        var c=p.Instance.GetComponent<SceneCoordinateComponent>();
        return c.Cell==cell && p.Cell==cell && c.TryGetWorldPosition(p.MapGrid,out var expected) && Vector3.Distance(p.transform.position,expected)<.0001f;
    }
    static void Checks()
    {
        var p=Object.FindObjectOfType<MetaObjectPreset>();
        Check("scene initial binding",p.IsBound && At(p,new Vector2Int(7,-4)));
        var c=p.Instance.GetComponent<SceneCoordinateComponent>();
        p.SetCell(new Vector2Int(8,-4)); c.SetCell(new Vector2Int(9,-4));
        var originalInstance=p.Instance;
        Check("F2 exact sequence",p.TryBind() && At(p,new Vector2Int(9,-4)),"cell="+p.Cell);
        Check("repeat bind stable",p.TryBind() && p.TryBind() && At(p,new Vector2Int(9,-4)) && ReferenceEquals(originalInstance,p.Instance));
        p.SetCell(new Vector2Int(-3,2));
        Check("preset setter then bind",p.TryBind() && At(p,new Vector2Int(-3,2)));
        c.SetCell(Vector2Int.zero);
        Check("explicit zero cell preserved",p.TryBind() && At(p,Vector2Int.zero));
        c.SetCell(new Vector2Int(11,-5)); p.Rebuild();
        Check("rebuild preserves latest coordinate",At(p,new Vector2Int(11,-5)) && !ReferenceEquals(originalInstance,p.Instance) && originalInstance.ComponentCount==0 && c.Owner==null && c.Preset==null);
        var temp=new GameObject("F2_Prebind"); temp.SetActive(false);
        temp.AddComponent<SpriteRenderer>(); var q=temp.AddComponent<MetaObjectPreset>();
        var serialized=new SerializedObject(q);
        serialized.FindProperty("definition").objectReferenceValue=p.Definition;
        serialized.FindProperty("grid").objectReferenceValue=p.MapGrid;
        serialized.FindProperty("rebuildOnAwake").boolValue=false;
        serialized.ApplyModifiedPropertiesWithoutUndo();
        q.SetCell(new Vector2Int(4,-2)); temp.SetActive(true);
        Check("prebind SetCell consumed",q.TryBind() && At(q,new Vector2Int(4,-2)));
        q.Instance.GetComponent<SceneCoordinateComponent>().SetCell(new Vector2Int(5,-2));
        Check("prebind cache does not replay",q.TryBind() && At(q,new Vector2Int(5,-2)));
        var definition=ScriptableObject.CreateInstance<MetaObjectDefinition>();
        var definitionsField=typeof(MetaObjectDefinition).GetField("componentDefinitions",BindingFlags.Instance|BindingFlags.NonPublic);
        definitionsField.SetValue(definition,new System.Collections.Generic.List<MetaObjectComponentDefinition>{new SceneCoordinateComponentDefinition(new Vector2(1.25f,-1.25f))});
        serialized.Update(); serialized.FindProperty("definition").objectReferenceValue=definition; serialized.ApplyModifiedPropertiesWithoutUndo();
        q.Rebuild();
        Check("rebuild keeps cell with crossing offset",At(q,new Vector2Int(5,-2)));
        q.Rebuild();
        Check("repeated rebuild offset stable",At(q,new Vector2Int(5,-2)));
        q.Instance.GetComponent<SceneCoordinateComponent>().SetCell(new Vector2Int(-8,0));
        Check("component setter and offset repeat bind",q.TryBind() && At(q,new Vector2Int(-8,0)));
        var sprite=SceneTextureComponent.LoadSprite("Assets/M Studio/Art/Characters/Player/Body/BodyWalkDown.png");
        var t=p.Instance.GetComponent<SceneTextureComponent>();
        Check("texture binding unaffected",sprite!=null && t.SetTexture(sprite) && p.TryBind() && p.Renderer.sprite==sprite);
        Object.DestroyImmediate(temp); Object.DestroyImmediate(definition);
        p.SetCell(new Vector2Int(7,-4));
        var wiring=MetaObjectVerification.Run();
        Check("scene wiring remains valid",wiring.StartsWith("METAOBJECT_VERIFY PASS"));
        report.AppendLine(wiring);
    }
}
