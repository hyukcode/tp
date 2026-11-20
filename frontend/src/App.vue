<script setup>
import { computed, onMounted, ref } from "vue";
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
async function api(path, body) {
  const response = await fetch(
    "/api/" + path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  if (!response.ok) throw Error(data.error);
  return data;
}
async function run(fn) {
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
    values: values.value,
  });
  output.value = JSON.stringify(data, null, 2);
  const url = URL.createObjectURL(
    new Blob([output.value], { type: "application/json" }),
  );
  const a = window.document.createElement("a");
  a.href = url;
  a.download = `template-${current.value.id}-v${version.value}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  message.value = "已导出，可用 tasker plan --template <文件路径> 加载。";
}
async function importFile(event) {
  const file = event.target.files[0];
  try {
    if (!file) return;
    if (dirty.value && !confirm("放弃未保存修改？")) return;
    document.value = await api("import", {
      name: file.name.replace(/\.[^.]+$/, ""),
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
window.onbeforeunload = (e) => {
  if (dirty.value) {
    e.preventDefault();
    e.returnValue = "";
  }
};
</script>
<template>
  <aside>
    <div class="brand">◈ Template Studio</div>
    <p>为 taskdispatcher 编写可复用的任务模板</p>
    <button :disabled="busy" @click="select(null)">新建模板</button
    ><label class="upload"
      >导入 Markdown<input
        type="file"
        accept=".md,.markdown,.txt"
        :disabled="busy"
        @change="run(() => importFile($event))"
    /></label>
    <h3>模板库</h3>
    <input v-model="query" placeholder="搜索名称或标签" aria-label="搜索模板" />
    <div id="library">
      <button
        v-for="record in filtered"
        :key="record.id"
        :disabled="busy"
        @click="select(record)"
      >
        {{ record.document.template_name || "未命名模板" }} ·
        {{ record.versions.length ? "v" + record.versions[0] : "草稿" }}
      </button>
      <p v-if="!filtered.length">暂无模板</p>
    </div>
  </aside>
  <main>
    <header>
      <div>
        <small>模板工作台 / 编辑</small>
        <h1>把经验变成可复用的任务</h1>
        <p>定义目标与验收标准，让 planner 负责规划与执行。</p>
      </div>
      <span id="state">{{
        dirty
          ? "有未保存修改"
          : current.id
            ? "草稿 · 修订 " + current.revision
            : "未保存草稿"
      }}</span>
    </header>
    <div class="toolbar">
      <button :disabled="busy" @click="run(save)">保存草稿</button
      ><button :disabled="busy" @click="run(validate)">校验</button
      ><button class="primary" :disabled="busy" @click="run(publish)">
        发布版本
      </button>
    </div>
    <p id="message" role="status" aria-live="polite">{{ message }}</p>
    <fieldset :disabled="busy" @input="dirty = true">
      <section>
        <h2>基本信息</h2>
        <div class="grid">
          <label
            >模板名称<input
              v-model="document.template_name"
              placeholder="例如：需求实现与验收" /></label
          ><label>标签<input v-model="tags" placeholder="开发, 验收" /></label>
        </div>
        <label
          >适用场景<textarea
            v-model="document.description"
            rows="2"
            placeholder="什么时候使用这个模板？"
          ></textarea></label
        ><label
          >规划上下文<textarea
            v-model="document.system_prompt_extension"
            rows="3"
            placeholder="例如：围绕需求制定计划"
          ></textarea>
        </label>
      </section>
      <section>
        <h2>输入参数<button @click="addParam">添加参数</button></h2>
        <p v-pre>在任务和上下文中使用 {{ 参数名 }}，预览时填写实际值。</p>
        <div
          v-for="(param, index) in document.parameters"
          :key="index"
          class="param"
        >
          <label
            >参数名<input
              v-model="param.name"
              placeholder="requirement" /></label
          ><label>默认值<input v-model="param.default" /></label
          ><label><input v-model="param.required" type="checkbox" />必填</label
          ><button @click="remove(document.parameters, index)">删除</button>
        </div>
      </section>
      <section>
        <h2>建议任务<button @click="addTask">添加任务</button></h2>
        <p v-if="!document.suggested_tasks.length">
          添加任务，描述目标、执行说明和验收标准。
        </p>
        <div
          v-for="(task, index) in document.suggested_tasks"
          :key="index"
          class="task"
        >
          <h3>
            任务 {{ index + 1
            }}<span
              ><button v-if="index" @click="up(index)">上移</button
              ><button @click="remove(document.suggested_tasks, index)">
                删除
              </button></span
            >
          </h3>
          <label>任务目标<input v-model="task.title" /></label
          ><label
            >执行说明<textarea v-model="task.description"></textarea></label
          ><label>工具要求（选填）<input v-model="task.tool" /></label
          ><label
            >验收标准<textarea v-model="task.acceptance"></textarea>
          </label>
        </div>
      </section>
    </fieldset>
    <section>
      <h2>预览与导出</h2>
      <p>发布保存模板定义；导出将参数填入指定版本，供 taskdispatcher 使用。</p>
      <label v-for="(param, index) in document.parameters" :key="index"
        >{{ param.name || "未命名参数"
        }}<input
          v-model="values[param.name]"
          :placeholder="param.default || '填写示例值'"
      /></label>
      <div class="toolbar">
        <button :disabled="busy" @click="run(preview)">预览当前草稿</button
        ><select v-model="version" aria-label="已发布版本">
          <option value="" disabled>选择发布版本</option>
          <option v-for="v in versions" :key="v" :value="v">
            发布版本 v{{ v }}
          </option></select
        ><button :disabled="busy || !version" @click="run(exportRelease)">
          导出发布版本
        </button>
      </div>
      <pre>{{ output }}</pre>
    </section>
  </main>
</template>
