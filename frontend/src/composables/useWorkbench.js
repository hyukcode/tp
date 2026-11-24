import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { request as api, downloadJson, fileStem } from "../api.js";

export function useWorkbench() {
  const blank = () => ({
    template_name: "",
    tags: [],
    description: "",
    system_prompt_extension: "",
    parameters: [],
    suggested_tasks: [],
  });
  const document = ref(blank()),
    records = ref([]),
    current = ref({ id: "", revision: 0 }),
    query = ref(""),
    message = ref("新建模板，或导入 Markdown 草稿。"),
    output = ref("填写示例参数后预览。"),
    values = ref({}),
    version = ref(""),
    dirty = ref(false),
    busy = ref(false);
  const filtered = computed(() =>
    records.value.filter((r) =>
      JSON.stringify([r.document.template_name, r.document.tags])
        .toLowerCase()
        .includes(query.value.toLowerCase()),
    ),
  );
  const versions = computed(
    () => records.value.find((r) => r.id === current.value.id)?.versions || [],
  );
  const tags = computed({
    get: () => document.value.tags?.join(", ") || "",
    set: (v) => {
      document.value.tags = v
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
    },
  });
  async function run(fn) {
    if (busy.value) return;
    busy.value = true;
    try {
      await fn();
    } catch (e) {
      message.value = e.message;
    } finally {
      busy.value = false;
    }
  }
  async function refresh() {
    records.value = await api("templates");
  }
  function select(record) {
    if (dirty.value && !confirm("放弃未保存修改？")) return;
    current.value = record
      ? { id: record.id, revision: record.revision }
      : { id: "", revision: 0 };
    document.value = record
      ? JSON.parse(JSON.stringify(record.document))
      : blank();
    document.value.parameters ||= [];
    values.value = {};
    version.value = record?.versions[0] || "";
    dirty.value = false;
    output.value = "填写示例参数后预览。";
  }
  async function save() {
    current.value = await api("save", {
      ...current.value,
      document: document.value,
    });
    dirty.value = false;
    await refresh();
    message.value = "草稿已保存。";
  }
  async function validate() {
    const result = await api("validate", { document: document.value });
    message.value = result.errors.length
      ? result.errors.join("\n")
      : "校验通过，可以发布。";
    return result.errors;
  }
  async function publish() {
    if ((await validate()).length) return;
    await save();
    const release = await api("publish", current.value);
    await refresh();
    version.value = release.version;
    message.value = `已发布 v${release.version}，后续编辑不会改变此版本。`;
  }
  async function preview() {
    output.value = JSON.stringify(
      await api("preview", { document: document.value, values: values.value }),
      null,
      2,
    );
    message.value = "当前草稿的实例化结果。";
  }
  async function exportRelease() {
    if (!version.value) throw Error("请先发布版本");
    const data = await api("release", {
      id: current.value.id,
      version: Number(version.value),
      values: releaseValues.value,
    });
    output.value = JSON.stringify(data, null, 2);
    downloadJson(data, `template-${current.value.id}-v${version.value}.json`);
    message.value = "已导出，可用 tasker plan --template <文件路径> 加载。";
  }
  async function importFile(event) {
    const file = event.target.files[0];
    try {
      if (!file) return;
      if (dirty.value && !confirm("放弃未保存修改？")) return;
      document.value = await api("import", {
        name: fileStem(file.name),
        content: await file.text(),
      });
      current.value = { id: "", revision: 0 };
      values.value = {};
      version.value = "";
      dirty.value = true;
      message.value = "已导入草稿，请补充并确认验收标准。";
    } finally {
      event.target.value = "";
    }
  }
  function addTask() {
    document.value.suggested_tasks.push({
      title: "",
      description: "",
      tool: "",
      acceptance: "",
    });
    dirty.value = true;
  }
  function addParam() {
    document.value.parameters.push({ name: "", default: "", required: true });
    dirty.value = true;
  }
  function remove(items, index) {
    items.splice(index, 1);
    dirty.value = true;
  }
  function up(index) {
    const tasks = document.value.suggested_tasks;
    [tasks[index - 1], tasks[index]] = [tasks[index], tasks[index - 1]];
    dirty.value = true;
  }
  onMounted(() => run(refresh));
  const beforeUnload = (e) => {
    if (dirty.value) {
      e.preventDefault();
      e.returnValue = "";
    }
  };

  onMounted(() => window.addEventListener("beforeunload", beforeUnload));
  onUnmounted(() => window.removeEventListener("beforeunload", beforeUnload));

  const releaseParameters = ref([]);
  const releaseValues = ref({});
  const definitionLoading = ref(false);
  const definitionError = ref("");
  watch(
    [() => current.value.id, version],
    async ([id, selectedVersion], _, onCleanup) => {
      let cancelled = false;
      onCleanup(() => {
        cancelled = true;
      });
      releaseParameters.value = [];
      releaseValues.value = {};
      definitionError.value = "";
      definitionLoading.value = Boolean(id && selectedVersion);
      if (!id || !selectedVersion) return;
      try {
        const definition = await api("definition", {
          id,
          version: Number(selectedVersion),
        });
        if (!cancelled) releaseParameters.value = definition.parameters || [];
      } catch (error) {
        if (!cancelled) definitionError.value = error.message;
      } finally {
        if (!cancelled) definitionLoading.value = false;
      }
    },
  );
  return {
    document,
    current,
    query,
    message,
    output,
    values,
    version,
    dirty,
    busy,
    filtered,
    versions,
    tags,
    select,
    run,
    save,
    validate,
    publish,
    preview,
    exportRelease,
    importFile,
    addTask,
    addParam,
    remove,
    up,
    releaseParameters,
    releaseValues,
    definitionLoading,
    definitionError,
  };
}
