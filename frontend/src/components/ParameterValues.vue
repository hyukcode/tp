<script setup>
defineProps({
  parameters: { type: Array, default: () => [] },
  modelValue: { type: Object, required: true },
});
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <label v-for="(parameter, index) in parameters" :key="index">
    {{ parameter.name || "未命名参数" }}
    <input
      :value="modelValue[parameter.name] ?? ''"
      :placeholder="parameter.default || '填写参数值'"
      @input="
        emit('update:modelValue', {
          ...modelValue,
          [parameter.name]: $event.target.value,
        })
      "
    />
  </label>
</template>
