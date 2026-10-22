using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

[InitializeOnLoad]
public static class RoleMove0Acceptance20261022
{
    const string Key = "RoleMove0Acceptance20261022";
    const string Dir = "D:/myspace/Git/this/Output/角色移动0-验收20261022/";
    static StringBuilder report = new StringBuilder();
    static int stage, firstFrame, failures;
    static double start;
    static RoleMove0Acceptance20261022()
    {
        if (SessionState.GetBool(Key, false)) Install();
    }
    public static void Run()
    {
        SessionState.SetBool(Key, true);
        EditorSceneManager.OpenScene("Assets/Scenes/PersistanceScene.unity", OpenSceneMode.Single);
        EditorSceneManager.OpenScene("Assets/Scenes/01.Field.unity", OpenSceneMode.Additive);
        EditorSceneManager.OpenScene("Assets/Scenes/UI.unity", OpenSceneMode.Additive);
        EditorSceneManager.OpenScene("Assets/Scenes/Template.unity", OpenSceneMode.Additive);
        Install();
        EditorApplication.isPlaying = true;
    }
    static void Install()
    {
        start = EditorApplication.timeSinceStartup;
        EditorApplication.update -= Tick;
        EditorApplication.update += Tick;
    }
    static void Tick()
    {
        if (EditorApplication.timeSinceStartup - start > 180)
        {
            report.AppendLine("INFRASTRUCTURE TIMEOUT"); Finish(2); return;
        }
        if (stage == 2 && !EditorApplication.isPlaying && !EditorApplication.isPlayingOrWillChangePlaymode)
        { Finish(failures == 0 ? 0 : 1); return; }
        if (!EditorApplication.isPlaying) return;
        EditorApplication.QueuePlayerLoopUpdate();
        if (stage == 0)
        {
            Application.runInBackground = true;
            firstFrame = Time.frameCount; stage = 1; return;
        }
        if (stage != 1 || Time.frameCount < firstFrame + 10) return;
        report.AppendLine("UTC " + DateTime.UtcNow.ToString("o") + " frames=" + firstFrame + "->" + Time.frameCount);
        try { Checks(); }
        catch (Exception ex) { report.AppendLine(ex.ToString()); failures++; }
        File.WriteAllText(Dir + "角色移动0-验收20261022_行为结果_v1.txt", report.ToString());
        stage = 2; EditorApplication.isPlaying = false;
    }
    static void Finish(int code)
    {
        SessionState.EraseBool(Key);
        report.AppendLine("RESULT failures=" + failures + " exit=" + code);
        File.WriteAllText(Dir + "角色移动0-验收20261022_行为结果_v1.txt", report.ToString());
        EditorApplication.update -= Tick;
        EditorApplication.Exit(code);
    }
    static void Check(string name, bool ok, string detail = "")
    {
        if (!ok) failures++;
        report.AppendLine((ok ? "PASS " : "FAIL ") + name + " " + detail);
    }
    static void Checks()
    {
        var presets = Object.FindObjectsOfType<MetaObjectPreset>(true);
        Check("scene preset count", presets.Length == 1, "count=" + presets.Length);
        var p = presets.Single(x => x.name == "Player");
        var c = p.Instance.GetComponent<SceneCoordinateComponent>();
        var t = p.Instance.GetComponent<SceneTextureComponent>();
        var originalCell = c.Cell;
        report.AppendLine("INITIAL bound=" + p.IsBound + " grid=" + p.MapGrid.gameObject.scene.name + "/" + p.MapGrid.name + " cell=" + c.Cell + " position=" + p.transform.position);
        Check("single-object player", p.transform.childCount == 0 && p.GetComponents<Component>().Length == 3);
        Check("initial binding", p.IsBound && !p.IsPendingBinding && p.Instance.ComponentCount == 2 && p.Definition.MetaObjectId == "CHAR_PLAYER");
        Check("cell center", c.Cell == new Vector2Int(7,-4) && Vector3.Distance(p.transform.position, p.MapGrid.GetCellCenterWorld(new Vector3Int(7,-4,0))) < .0001f);
        Check("empty texture intentional", t.Texture == null && string.IsNullOrEmpty(t.TexturePath) && p.Renderer.sprite == null);
        var camera = Object.FindObjectOfType<Cinemachine.CinemachineVirtualCamera>();
        Check("camera wiring", camera != null && camera.Follow == p.transform && camera.LookAt == p.transform);
        Check("old layered prefab preserved", AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Player_Layered.prefab").GetComponentsInChildren<SpriteRenderer>(true).Length == 4);
        report.AppendLine(MetaObjectVerification.Run());
        Capture("角色移动0-验收20261022_空纹理_v1.png");
        p.SetCell(new Vector2Int(8,-4));
        Check("preset.SetCell moves", c.Cell == new Vector2Int(8,-4) && Vector3.Distance(p.transform.position, p.MapGrid.GetCellCenterWorld(new Vector3Int(8,-4,0))) < .0001f);
        c.SetCell(new Vector2Int(9,-4));
        Check("coordinate.SetCell moves", p.Cell == new Vector2Int(9,-4) && Vector3.Distance(p.transform.position, p.MapGrid.GetCellCenterWorld(new Vector3Int(9,-4,0))) < .0001f);
        const string path = "Assets/M Studio/Art/Characters/Player/Body/BodyWalkDown.png";
        var sprites = AssetDatabase.LoadAllAssetsAtPath(path).OfType<Sprite>().ToArray();
        Check("existing sprite available", sprites.Length > 1, "sprites=" + sprites.Length);
        var s = sprites[0];
        Check("SetTexture assigns renderer", t.SetTexture(s) && p.Renderer.sprite == s);
        var panel = Object.FindObjectOfType<DebugPanel>();
        Check("debug panel exists", panel != null);
        var cycle = typeof(DebugPanel).GetMethod("CycleTexture", BindingFlags.Instance | BindingFlags.NonPublic);
        cycle.Invoke(panel, new object[]{p});
        var beforeCycle = t.Texture;
        cycle.Invoke(panel, new object[]{p});
        Check("debug texture cycle changes sprite", t.Texture != beforeCycle, "before=" + beforeCycle.name + " after=" + t.Texture.name);
        Check("invalid path rejected and preserved", !t.SetTexturePath("Assets/__acceptance_missing__.png") && t.Texture == s && p.Renderer.sprite == s);
        Check("null rejected and preserved", !t.SetTexture(null) && t.Texture == s && p.Renderer.sprite == s);
        Check("path assignment", t.SetTexturePath(path) && p.Renderer.sprite == t.Texture && t.Texture != null);
        Capture("角色移动0-验收20261022_赋纹理并改坐标_v1.png");
        var directCell = c.Cell;
        p.TryBind();
        Check("repeated TryBind preserves component coordinate", c.Cell == directCell, "before=" + directCell + " after=" + c.Cell);
        p.SetCell(originalCell);
        var oldInstance = p.Instance;
        p.Rebuild();
        Check("Rebuild releases old components", !ReferenceEquals(p.Instance,oldInstance) && oldInstance.ComponentCount == 0 && c.Owner == null && c.Preset == null && p.IsBound && p.Cell == originalCell);
        var added = new SceneCoordinateComponent(Vector2.zero);
        p.Instance.AddComponent(added);
        added.SetCell(new Vector2Int(10,-4));
        Check("runtime component replacement remains usable", added.IsBound && Vector3.Distance(p.transform.position,p.MapGrid.GetCellCenterWorld(new Vector3Int(10,-4,0))) < .0001f, "presetBound=" + p.IsBound + " componentBound=" + added.IsBound + " position=" + p.transform.position);
        p.Rebuild();
        var a = new MetaObjectInstance("A"); var b = new MetaObjectInstance("B");
        var shared = new SceneCoordinateComponent(Vector2.zero);
        a.AddComponent(shared); b.AddComponent(shared); a.Dispose();
        Check("component ownership isolation", b.GetComponent<SceneCoordinateComponent>().Owner == b, "B component owner=" + (shared.Owner == null ? "null" : shared.Owner.MetaObjectId));
        b.Dispose();
        p.gameObject.SetActive(false);
        Check("disabled object unbinds components", !p.IsBound && !p.Instance.GetComponent<SceneCoordinateComponent>().IsBound);
        p.gameObject.SetActive(true);
        var hide = p.gameObject;
        Object.DestroyImmediate(hide);
        string noObjectReport = MetaObjectVerification.Run();
        Check("verification rejects zero targets", !noObjectReport.StartsWith("METAOBJECT_VERIFY PASS"), noObjectReport.Trim());
    }
    static void Capture(string filename)
    {
        var camera = Camera.main;
        if (camera == null) { report.AppendLine("CAPTURE unavailable no main camera"); return; }
        var previous = camera.targetTexture;
        var active = RenderTexture.active;
        var rt = RenderTexture.GetTemporary(1280,720,24);
        camera.targetTexture = rt; camera.Render(); RenderTexture.active = rt;
        var image = new Texture2D(1280,720,TextureFormat.RGB24,false);
        image.ReadPixels(new Rect(0,0,1280,720),0,0); image.Apply();
        File.WriteAllBytes(Dir + filename,image.EncodeToPNG());
        camera.targetTexture = previous; RenderTexture.active = active;
        Object.DestroyImmediate(image); RenderTexture.ReleaseTemporary(rt);
        report.AppendLine("CAPTURE " + filename + " (Camera.Render; UI/IMGUI excluded)");
    }
}
