<script setup>
import { useWorkbench } from "./composables/useWorkbench.js";
import ParameterValues from "./components/ParameterValues.vue";
const {
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
} = useWorkbench();
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
      <h3>草稿参数</h3>
      <ParameterValues :parameters="document.parameters" v-model="values" />
      <div class="toolbar">
        <button :disabled="busy" @click="run(preview)">预览当前草稿</button
        ><select v-model="version" aria-label="已发布版本">
          <option value="" disabled>选择发布版本</option>
          <option v-for="v in versions" :key="v" :value="v">
            发布版本 v{{ v }}
          </option></select
        ><button
          :disabled="
            busy || !version || definitionLoading || Boolean(definitionError)
          "
          @click="run(exportRelease)"
        >
          导出发布版本
        </button>
      </div>
      <h3 v-if="version">发布版本 v{{ version }} 的参数</h3>
      <p v-if="definitionLoading">正在加载版本参数…</p>
      <p v-if="definitionError" role="alert">{{ definitionError }}</p>
      <ParameterValues
        :parameters="releaseParameters"
        v-model="releaseValues"
      />
      <pre>{{ output }}</pre>
    </section>
  </main>
</template>
