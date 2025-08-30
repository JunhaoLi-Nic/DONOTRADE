<script setup>
import { ref, onMounted } from 'vue';

const props = defineProps({
  playbook: {
    type: Object,
    required: true
  }
});

// Notes content
const notes = ref('');
const isEditing = ref(false);
const editableNotes = ref('');

// Load notes from playbook or use default
onMounted(() => {
  if (props.playbook && props.playbook.notes) {
    notes.value = props.playbook.notes;
  } else {
    notes.value = 'No notes have been added for this playbook yet. Click "Edit Notes" to add some.';
  }
  editableNotes.value = notes.value;
});

// Edit mode functions
function startEditing() {
  editableNotes.value = notes.value;
  isEditing.value = true;
}

function saveNotes() {
  notes.value = editableNotes.value;
  isEditing.value = false;
  
  // Here you would typically save the notes to the backend
  console.log('Notes saved:', notes.value);
}

function cancelEditing() {
  editableNotes.value = notes.value;
  isEditing.value = false;
}
</script>

<template>
  <div class="notes-container">
    <div class="notes-header">
      <h3 class="notes-title">Playbook Notes</h3>
      <div v-if="!isEditing" class="notes-actions">
        <button class="btn-edit" @click="startEditing">
          <i class="uil uil-edit"></i> Edit Notes
        </button>
      </div>
      <div v-else class="notes-actions">
        <button class="btn-cancel" @click="cancelEditing">
          Cancel
        </button>
        <button class="btn-save" @click="saveNotes">
          Save Notes
        </button>
      </div>
    </div>
    
    <div class="notes-body">
      <!-- View mode -->
      <div v-if="!isEditing" class="notes-content">
        {{ notes }}
      </div>
      
      <!-- Edit mode -->
      <div v-else class="notes-edit">
        <textarea 
          v-model="editableNotes"
          class="notes-textarea"
          placeholder="Enter your notes about this playbook here..."
        ></textarea>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notes-container {
  background-color: #252525;
  border-radius: 0.5rem;
  overflow: hidden;
}

.notes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #1e1e1e;
  border-bottom: 1px solid #333;
}

.notes-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 500;
}

.notes-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-edit,
.btn-cancel,
.btn-save {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-edit {
  background: none;
  border: 1px solid #5e72e4;
  color: #5e72e4;
}

.btn-edit:hover {
  background-color: rgba(94, 114, 228, 0.1);
}

.btn-cancel {
  background: none;
  border: 1px solid #333;
  color: #fff;
}

.btn-cancel:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.btn-save {
  background-color: #5e72e4;
  border: none;
  color: #fff;
}

.btn-save:hover {
  background-color: #4a5cd0;
}

.notes-body {
  padding: 1rem;
}

.notes-content {
  white-space: pre-wrap;
  line-height: 1.6;
  min-height: 200px;
}

.notes-edit {
  width: 100%;
}

.notes-textarea {
  width: 100%;
  min-height: 300px;
  padding: 1rem;
  background-color: #1e1e1e;
  border: 1px solid #333;
  border-radius: 0.375rem;
  color: #fff;
  font-size: 1rem;
  line-height: 1.6;
  resize: vertical;
}

.notes-textarea:focus {
  outline: none;
  border-color: #5e72e4;
}
</style> 