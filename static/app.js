/**
 * Constraint Satisfaction Timetable Scheduler
 * Frontend Application Controller with Visual Form Configuration Studio
 * Protocol: Premium Utilitarian Minimalism & Editorial UI.
 */

// LocalStorage Persistence Key
const STORAGE_KEY = 'AI_TIMETABLE_CUSTOM_DATA_V2';

// Application State
const state = {
  currentData: null,
  rawConfig: null,
  customData: null, // User's mutable institutional data structure
  sessions: [],
  asg: {},
  report: null,
  history: [], // Stack for Undo functionality
  currentPerspective: 'class',
  selectedEntity: '',
  activeTab: 'tab-data',
};

// DOM Elements
const elements = {
  navTabs: document.querySelectorAll('.tab-btn'),
  tabPanels: document.querySelectorAll('.tab-panel'),
  globalNotice: document.getElementById('global-notice'),
  btnLoadSmall: document.getElementById('btn-load-small'),
  btnLoadLarge: document.getElementById('btn-load-large'),
  btnDownloadTpl: document.getElementById('btn-download-tpl'),
  jsonFileInput: document.getElementById('json-file-input'),
  loadedBadge: document.getElementById('loaded-dataset-badge'),
  datasetSummaryText: document.getElementById('dataset-summary-text'),
  feasibilityGrid: document.getElementById('feasibility-grid'),
  feasibilityBadge: document.getElementById('feasibility-overall-badge'),
  tableClasses: document.getElementById('table-classes-container'),
  tableRooms: document.getElementById('table-rooms-container'),
  tableTeachers: document.getElementById('table-teachers-container'),
  tableSubjects: document.getElementById('table-subjects-container'),
  timeSlotsDisplay: document.getElementById('time-slots-display'),
  solveForm: document.getElementById('solve-form'),
  selectAlgo: document.getElementById('select-algo'),
  inputSeed: document.getElementById('input-seed'),
  inputTimeout: document.getElementById('input-timeout'),
  btnRunSolve: document.getElementById('btn-run-solve'),
  solutionBadge: document.getElementById('solution-status-badge'),
  metricTime: document.getElementById('metric-time'),
  metricHard: document.getElementById('metric-hard'),
  metricSoft: document.getElementById('metric-soft'),
  metricWork: document.getElementById('metric-work'),
  traceContainer: document.getElementById('trace-container'),
  traceChart: document.getElementById('trace-chart'),
  perspButtons: document.querySelectorAll('[data-perspective]'),
  selectEntity: document.getElementById('select-entity'),
  matrixContainer: document.getElementById('timetable-matrix-container'),
  osWindowTitle: document.getElementById('os-window-title'),
  diagnosticsList: document.getElementById('diagnostics-list'),
  editSession: document.getElementById('edit-select-session'),
  editDay: document.getElementById('edit-select-day'),
  editPeriod: document.getElementById('edit-select-period'),
  editRoom: document.getElementById('edit-select-room'),
  diffHard: document.getElementById('diff-hard'),
  diffSoft: document.getElementById('diff-soft'),
  trialConflictAlerts: document.getElementById('trial-conflict-alerts'),
  btnApplyMove: document.getElementById('btn-apply-move'),
  btnUndoMove: document.getElementById('btn-undo-move'),
  undoCount: document.getElementById('undo-count'),
  btnSuggestSlots: document.getElementById('btn-suggest-slots'),
  suggestedContainer: document.getElementById('suggested-slots-container'),
  suggestedList: document.getElementById('suggested-slots-list'),
  btnExportCsv: document.getElementById('btn-export-csv'),
  btnExportJson: document.getElementById('btn-export-json'),
  btnPrintMatrix: document.getElementById('btn-print-matrix'),
  benchmarkContainer: document.getElementById('benchmark-tables-container'),

  // Form Studio Buttons
  btnAddBatch: document.getElementById('btn-add-batch'),
  btnAddBatchCard: document.getElementById('btn-add-batch-card'),
  btnAddTeacher: document.getElementById('btn-add-teacher'),
  btnAddTeacherCard: document.getElementById('btn-add-teacher-card'),
  btnAddRoom: document.getElementById('btn-add-room'),
  btnAddRoomCard: document.getElementById('btn-add-room-card'),
  btnAddSubject: document.getElementById('btn-add-subject'),
  btnAddSubjectCard: document.getElementById('btn-add-subject-card'),
  btnOpenTimeModal: document.getElementById('btn-open-time-modal'),
  btnQuickEditTime: document.getElementById('btn-quick-edit-time'),
  btnSaveDisk: document.getElementById('btn-save-disk'),
  btnResetCustom: document.getElementById('btn-reset-custom'),

  // Modals & Forms
  modalBatch: document.getElementById('modal-batch'),
  batchForm: document.getElementById('batch-form'),
  batchEditOriginal: document.getElementById('batch-edit-original'),
  batchName: document.getElementById('batch-name'),
  batchSemTypeOdd: document.getElementById('batch-sem-type-odd'),
  batchSemTypeEven: document.getElementById('batch-sem-type-even'),
  batchSemester: document.getElementById('batch-semester'),
  batchStrength: document.getElementById('batch-strength'),
  batchSplitPreview: document.getElementById('batch-split-preview'),
  batchAutoSplit: document.getElementById('batch-auto-split'),
  batchLunch: document.getElementById('batch-lunch'),
  batchTheoryCheckboxes: document.getElementById('batch-theory-checkboxes'),
  batchLabCheckboxes: document.getElementById('batch-lab-checkboxes'),

  modalTeacher: document.getElementById('modal-teacher'),
  teacherForm: document.getElementById('teacher-form'),
  teacherEditOriginal: document.getElementById('teacher-edit-original'),
  teacherName: document.getElementById('teacher-name'),
  teacherMaxLoad: document.getElementById('teacher-max-load'),
  teacherSubjectsCheckboxes: document.getElementById('teacher-subjects-checkboxes'),
  teacherAvoidPeriods: document.getElementById('teacher-avoid-periods'),
  teacherUnavailGridContainer: document.getElementById('teacher-unavail-grid-container'),

  modalRoom: document.getElementById('modal-room'),
  roomForm: document.getElementById('room-form'),
  roomEditOriginal: document.getElementById('room-edit-original'),
  roomName: document.getElementById('room-name'),
  roomType: document.getElementById('room-type'),
  roomCapacity: document.getElementById('room-capacity'),

  modalSubject: document.getElementById('modal-subject'),
  subjectForm: document.getElementById('subject-form'),
  subjectEditOriginal: document.getElementById('subject-edit-original'),
  subjectCode: document.getElementById('subject-code'),
  subjectName: document.getElementById('subject-name'),
  subjectTypeTheory: document.getElementById('subject-type-theory'),
  subjectTypeLab: document.getElementById('subject-type-lab'),
  subjectHours: document.getElementById('subject-hours'),
  subjectLabBlock: document.getElementById('subject-lab-block'),
  subjectLabBlockGroup: document.getElementById('subject-lab-block-group'),

  modalTime: document.getElementById('modal-time'),
  timeForm: document.getElementById('time-form'),
  timeStart: document.getElementById('time-start'),
  timeEnd: document.getElementById('time-end'),
  timePeriodsCount: document.getElementById('time-periods-count'),
  timeLunchPeriod: document.getElementById('time-lunch-period'),
  timeSlotsModalPreview: document.getElementById('time-slots-modal-preview'),
  timeDaysPills: document.getElementById('time-days-pills'),
};

// Teacher Modal interactive unavailable tracker: Set of string "Day_Period"
let teacherUnavailSelection = new Set();

// =============================================================================
// Helper: 9:00 AM – 5:00 PM Slot Generator
// =============================================================================
function generate9to5Slots(periodsCount = 8, lunchPeriod = 5) {
  const count = Math.min(Math.max(parseInt(periodsCount, 10) || 8, 5), 8);
  const slots = [];
  const startHour = 9; // 9:00 AM minimum
  for (let i = 0; i < count; i++) {
    const sH = startHour + i;
    const eH = sH + 1;
    const formatTime = (h) => {
      const period = h >= 12 ? 'PM' : 'AM';
      let hour12 = h % 12;
      if (hour12 === 0) hour12 = 12;
      const strH = String(hour12).padStart(2, '0');
      return `${strH}:00 ${period}`;
    };
    const sStr = formatTime(sH);
    const eStr = formatTime(eH);
    const pNum = i + 1;
    slots.push({
      period: pNum,
      name: `${sStr} - ${eStr}`,
      start: `${String(sH).padStart(2, '0')}:00`,
      end: `${String(eH).padStart(2, '0')}:00`,
      is_lunch: (pNum === parseInt(lunchPeriod, 10))
    });
  }
  return slots;
}

// =============================================================================
// Sub-batch Lab Division Engine
// Divides batches of size 30, 60, 90, 120 into sub-batches of 30 for lab rooms
// =============================================================================
function compileSolverData(custom) {
  const copy = JSON.parse(JSON.stringify(custom));
  const compiledClasses = [];
  const LAB_CAPACITY = 90; // Lab capacity threshold for splitting batches

  for (const b of (copy.batches || [])) {
    const strength = parseInt(b.strength, 10) || 30;
    const theorySubjects = b.subjects || [];
    const labSubjects = b.labs || [];
    const lunchPeriod = parseInt(b.lunch_period, 10) || 4;

    // Split labs only when batch strength is exactly 120.
    // Theory lectures stay in a single parent class of full strength.
    if (b.auto_split !== false && labSubjects.length > 0 && strength === 120) {
      const k = 2; // Always two sub-batches of 60
      // Parent class for theory (full batch)
      if (theorySubjects.length > 0) {
        compiledClasses.push({
          name: b.name,
          strength: strength,
          subjects: theorySubjects,
          lunch_period: lunchPeriod,
          teacher_map: b.teacher_map || {},
          parent_batch: b.name,
          semester: b.semester
        });
      }
      // Sub‑batches for labs, each size <= LAB_CAPACITY (distributed evenly)
      for (let i = 1; i <= k; i++) {
        const subStrength = 60; // Each sub-batch is half of 120
        compiledClasses.push({
          name: `${b.name}${i}`,
          strength: subStrength,
          subjects: labSubjects,
          lunch_period: lunchPeriod,
          teacher_map: b.teacher_map || {},
          parent_batch: b.name,
          sub_index: i,
          semester: b.semester
        });
      }
    } else {
      // No split needed (strength ≤ LAB_CAPACITY or no labs): single cohort gets all subjects
      const allSubjects = [...theorySubjects, ...labSubjects];
      compiledClasses.push({
        name: b.name,
        strength: strength,
        subjects: allSubjects,
        lunch_period: lunchPeriod,
        teacher_map: b.teacher_map || {},
        semester: b.semester
      });
    }
  }

  copy.classes = compiledClasses;
  return copy;
}

// =============================================================================
// Default Institutional Template
// =============================================================================
function createDefaultCustomData() {
  const periodSlots = generate9to5Slots(8, 5); // 8 periods, 9:00 AM - 5:00 PM, Lunch at P5 (1:00 PM - 2:00 PM)
  return {
    time: {
      days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
      periods_per_day: 8,
      break_periods: [],
      lab_block: 2,
      period_slots: periodSlots,
    },
    subjects: [
      { code: "CS101", name: "Programming Foundations", hours: 4, type: "theory" },
      { code: "CS102", name: "Data Structures", hours: 4, type: "theory" },
      { code: "MATH1", name: "Discrete Mathematics", hours: 3, type: "theory" },
      { code: "CS101P", name: "Programming Lab", hours: 2, type: "lab" },
      { code: "CS102P", name: "Data Structures Lab", hours: 2, type: "lab" },
      { code: "AI301", name: "Artificial Intelligence", hours: 4, type: "theory" },
      { code: "AI301P", name: "AI & Machine Learning Lab", hours: 2, type: "lab" }
    ],
    rooms: [
      { name: "LT-101", capacity: 150, type: "lecture_theatre" },
      { name: "TR-201", capacity: 60, type: "tutorial_room" },
      { name: "CR-102", capacity: 60, type: "classroom" },
      { name: "CR-103", capacity: 60, type: "classroom" },
      { name: "Lab-A", capacity: 30, type: "lab" },
      { name: "Lab-B", capacity: 30, type: "lab" },
      { name: "Lab-C", capacity: 30, type: "lab" }
    ],
    teachers: [
      { name: "Dr. Alan Turing", subjects: ["CS101", "CS101P", "AI301", "AI301P"], max_load: 18, unavailable: [["Mon", 1]], avoid_periods: [1] },
      { name: "Prof. Ada Lovelace", subjects: ["CS102", "CS102P", "MATH1"], max_load: 18, unavailable: [["Fri", 7]], avoid_periods: [7] },
      { name: "Dr. Claude Shannon", subjects: ["CS101", "CS101P", "MATH1"], max_load: 16, unavailable: [], avoid_periods: [2] },
      { name: "Prof. Grace Hopper", subjects: ["CS102", "CS102P", "AI301", "AI301P"], max_load: 18, unavailable: [], avoid_periods: [] }
    ],
    batches: [
      {
        name: "CSE-A",
        semester: 3,
        sem_type: "odd",
        strength: 120, // Will automatically divide into 4 lab sub-batches: CSE-A1, CSE-A2, CSE-A3, CSE-A4
        auto_split: true,
        lunch_period: 5, // Sem 3+ → 1:00 PM - 2:00 PM
        subjects: ["CS101", "CS102", "MATH1"],
        labs: ["CS101P", "CS102P"],
        teacher_map: {}
      },
      {
        name: "AI-1",
        semester: 1,
        sem_type: "odd",
        strength: 60, // Will automatically divide into 2 lab sub-batches: AI-11, AI-12
        auto_split: true,
        lunch_period: 4, // Sem 1 & 2 → 12:00 PM - 1:00 PM
        subjects: ["CS101", "AI301"],
        labs: ["AI301P"],
        teacher_map: {}
      }
    ]
  };
}

// =============================================================================
// Initialization
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupAccordions();
  setupEventListeners();
  setupModalHandlers();
  initializeCustomStudio();
  loadBenchmarks();
});

function setupNavigation() {
  elements.navTabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      elements.navTabs.forEach(b => b.classList.remove('active'));
      elements.tabPanels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPanel = document.getElementById(target);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }
      state.activeTab = target;

      if (target === 'tab-views') {
        renderTimetableMatrix();
      } else if (target === 'tab-edit') {
        initManualEditor();
      } else if (target === 'tab-benchmarks') {
        loadBenchmarks();
      }
    });
  });
}

function setupAccordions() {
  document.querySelectorAll('.accordion-trigger').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const body = trigger.nextElementSibling;
      const span = trigger.querySelector('span');
      if (body.style.display === 'none') {
        body.style.display = 'block';
        if (span) span.textContent = '−';
      } else {
        body.style.display = 'none';
        if (span) span.textContent = '+';
      }
    });
  });
}

function setupEventListeners() {
  // Preset buttons
  elements.btnLoadSmall.addEventListener('click', () => loadPresetDataset('small'));
  elements.btnLoadLarge.addEventListener('click', () => loadPresetDataset('large'));
  elements.btnDownloadTpl.addEventListener('click', () => downloadTemplate());
  elements.btnResetCustom.addEventListener('click', resetCustomStudioData);
  elements.btnSaveDisk.addEventListener('click', saveCustomDataToDisk);

  // File upload
  elements.jsonFileInput.addEventListener('change', handleFileUpload);

  // Solver form
  elements.solveForm.addEventListener('submit', handleSolveSubmit);

  // Perspective buttons
  elements.perspButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      elements.perspButtons.forEach(b => b.classList.remove('active-perspective'));
      btn.classList.add('active-perspective');
      state.currentPerspective = btn.dataset.perspective;
      updatePerspectiveDropdown();
      renderTimetableMatrix();
    });
  });

  elements.selectEntity.addEventListener('change', () => {
    state.selectedEntity = elements.selectEntity.value;
    renderTimetableMatrix();
  });

  // Manual Editor inputs
  elements.editSession.addEventListener('change', () => {
    syncEditInputsWithSelectedSession();
    runTrialEvaluation();
  });
  elements.editDay.addEventListener('change', runTrialEvaluation);
  elements.editPeriod.addEventListener('change', runTrialEvaluation);
  elements.editRoom.addEventListener('change', runTrialEvaluation);

  elements.btnApplyMove.addEventListener('click', handleApplyMove);
  elements.btnUndoMove.addEventListener('click', handleUndoMove);
  elements.btnSuggestSlots.addEventListener('click', handleSuggestSlots);

  // Exports
  elements.btnExportCsv.addEventListener('click', exportCsv);
  elements.btnExportJson.addEventListener('click', exportJson);
  if (elements.btnPrintMatrix) {
    elements.btnPrintMatrix.addEventListener('click', handlePrintMatrix);
  }
}

// =============================================================================
// Custom Form Configuration Studio Setup
// =============================================================================
async function initializeCustomStudio() {
  // Check LocalStorage first
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      state.customData = JSON.parse(stored);
      showNotice('Restored your saved institutional configuration from local storage.', 'blue');
    } catch (e) {
      state.customData = createDefaultCustomData();
    }
  } else {
    // Check if custom.json exists on server
    try {
      const res = await fetch('/api/dataset/custom');
      if (res.ok) {
        const serverData = await res.json();
        if (serverData && serverData.classes) {
          state.customData = serverData;
        } else {
          state.customData = createDefaultCustomData();
        }
      } else {
        state.customData = createDefaultCustomData();
      }
    } catch (e) {
      state.customData = createDefaultCustomData();
    }
  }

  // Upgrade to 8 periods (9 AM - 5 PM) if currently < 8
  if (state.customData && state.customData.time && (state.customData.time.periods_per_day || 0) < 8) {
    state.customData.time.periods_per_day = 8;
    state.customData.time.period_slots = generate9to5Slots(
      8,
      state.customData.batches?.[0]?.lunch_period || 5
    );
  }

  // Ensure period_slots are present (always 9 AM - 5 PM)
  if (!state.customData.time.period_slots || state.customData.time.period_slots.length === 0) {
    state.customData.time.period_slots = generate9to5Slots(
      state.customData.time.periods_per_day || 8,
      state.customData.batches?.[0]?.lunch_period || 5
    );
  }

  await applyCustomDataAndUpdateUI(false);
}

function persistCustomData() {
  if (state.customData) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.customData));
  }
}

async function saveCustomDataToDisk() {
  if (!state.customData) return;
  persistCustomData();
  const compiled = compileSolverData(state.customData);
  try {
    const res = await fetch('/api/dataset/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(compiled)
    });
    const result = await res.json();
    if (result.saved) {
      showNotice('Institutional configuration successfully saved to server disk and local storage.', 'green');
    } else {
      showNotice(`Saved with validation warnings: ${result.errors.join('; ')}`, 'yellow');
    }
  } catch (err) {
    showNotice(`Error saving to disk: ${err.message}`, 'red');
  }
}

function resetCustomStudioData() {
  if (!confirm('Are you sure you want to reset all batches, teachers, rooms, and courses to defaults?')) {
    return;
  }
  localStorage.removeItem(STORAGE_KEY);
  state.customData = createDefaultCustomData();
  applyCustomDataAndUpdateUI(true);
  showNotice('Configuration reset to default university template.', 'blue');
}

async function applyCustomDataAndUpdateUI(notify = true) {
  persistCustomData();
  const compiled = compileSolverData(state.customData);
  state.currentData = compiled;
  state.rawConfig = compiled;

  // Feasibility Check
  try {
    const feasRes = await fetch('/api/feasibility', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(compiled),
    });
    const feasData = await feasRes.json();

    elements.loadedBadge.textContent = 'CUSTOM CONFIG ACTIVE';
    elements.loadedBadge.className = 'badge badge-green';
    const totalBatches = state.customData.batches.length;
    const totalClasses = compiled.classes.length;
    const labSubBatches = compiled.classes.filter(c => c.sub_index).length;
    const theoryClasses = totalClasses - labSubBatches;
    elements.datasetSummaryText.textContent = `${totalBatches} Batches → ${theoryClasses} Theory Class${theoryClasses !== 1 ? 'es' : ''} + ${labSubBatches} Lab Sub-Batch${labSubBatches !== 1 ? 'es' : ''} · ${state.customData.teachers.length} Faculty · ${state.customData.rooms.length} Rooms · 9 AM - 5 PM (${state.customData.time.periods_per_day} Periods)`;

    renderFeasibility(feasData.checks, feasData.feasible);
    renderAllStudioTables();
    renderTimeSlotsDisplay();
    updatePerspectiveDropdown();

    if (notify) {
      if (feasData.feasible) {
        showNotice('Configuration updated. All feasibility conditions passed!', 'green');
      } else {
        showNotice('Configuration updated. Note: Feasibility issues flagged below.', 'yellow');
      }
    }
  } catch (err) {
    showNotice(`Feasibility error: ${err.message}`, 'red');
  }
}

// =============================================================================
// Studio Tables Rendering
// =============================================================================
function renderAllStudioTables() {
  if (!state.customData) return;
  renderBatchesTable();
  renderTeachersTable();
  renderRoomsTable();
  renderSubjectsTable();
}

function renderTimeSlotsDisplay() {
  const time = state.customData?.time;
  if (!time || !time.period_slots) return;

  elements.timeSlotsDisplay.innerHTML = time.period_slots.map(slot => `
    <div class="time-slot-tile ${slot.is_lunch ? 'is-lunch' : ''}">
      <div class="slot-pnum">Period ${slot.period}</div>
      <div class="slot-time">${escapeHtml(slot.name)}</div>
    </div>
  `).join('');
}

function renderBatchesTable() {
  const batches = state.customData.batches || [];
  if (batches.length === 0) {
    elements.tableClasses.innerHTML = `
      <p style="color: var(--text-muted); font-size: 0.9rem; padding: 12px 0;">
        No batches added yet. Click <strong>Add Batch</strong> to define student cohorts.
      </p>
    `;
    return;
  }

  const periodSlots = state.customData.time.period_slots || [];

  elements.tableClasses.innerHTML = `
    <table style="width: 100%;">
      <thead>
        <tr>
          <th>Batch Identifier</th>
          <th>Semester</th>
          <th>Total Strength</th>
          <th>Lab Division (Capacity 30)</th>
          <th>Lunch Break</th>
          <th>Assigned Subjects & Labs</th>
          <th style="text-align: right;">Actions</th>
        </tr>
      </thead>
      <tbody>
        ${batches.map(b => {
          const strength = parseInt(b.strength, 10) || 30;
          const k = Math.ceil(strength / 30);
          const hasLabs = (b.labs || []).length > 0;
          const splitBadge = (b.auto_split !== false && strength > 30 && hasLabs)
            ? `<span class="badge badge-blue">Labs: ${k} Sub-Batches (${escapeHtml(b.name)}1..${escapeHtml(b.name)}${k} × 30)</span> <span class="badge badge-green">Theory: Full Batch (${strength})</span>`
            : `<span class="badge badge-green">Single Cohort (${strength})</span>`;

          const lunchSlot = periodSlots.find(p => p.period === parseInt(b.lunch_period, 10));
          const lunchLabel = lunchSlot ? `P${lunchSlot.period} (${lunchSlot.name})` : `Period ${b.lunch_period}`;

          const theoryTags = (b.subjects || []).map(s => `<span class="badge badge-green">${escapeHtml(s)}</span>`).join(' ');
          const labTags = (b.labs || []).map(l => `<span class="badge badge-blue">${escapeHtml(l)} (Lab)</span>`).join(' ');

          return `
            <tr>
              <td><strong>${escapeHtml(b.name)}</strong></td>
              <td><span class="badge badge-yellow">Sem ${b.semester || 1} (${(b.sem_type || 'odd').toUpperCase()})</span></td>
              <td><strong>${strength}</strong> students</td>
              <td>${splitBadge}</td>
              <td><code style="font-family: var(--font-mono); font-size: 0.78rem;">${escapeHtml(lunchLabel)}</code></td>
              <td>${theoryTags} ${labTags || '<span style="color:var(--text-muted);">None</span>'}</td>
              <td style="text-align: right;">
                <button type="button" class="btn-table-action" onclick="window.editBatchItem('${escapeHtml(b.name)}')">Edit</button>
                <button type="button" class="btn-table-action btn-del" onclick="window.deleteBatchItem('${escapeHtml(b.name)}')">Delete</button>
              </td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

function renderTeachersTable() {
  const teachers = state.customData.teachers || [];
  if (teachers.length === 0) {
    elements.tableTeachers.innerHTML = `
      <p style="color: var(--text-muted); font-size: 0.9rem; padding: 12px 0;">
        No faculty added yet. Click <strong>Add Teacher</strong> to register instructors.
      </p>
    `;
    return;
  }

  elements.tableTeachers.innerHTML = `
    <table style="width: 100%;">
      <thead>
        <tr>
          <th>Faculty Member</th>
          <th>Qualified Subjects</th>
          <th>Max Load</th>
          <th>Avoided Periods</th>
          <th>Hard Unavailable Slots</th>
          <th style="text-align: right;">Actions</th>
        </tr>
      </thead>
      <tbody>
        ${teachers.map(t => {
          const subjectsTags = (t.subjects || []).map(s => `<code style="font-family:var(--font-mono); font-size:0.78rem;">${escapeHtml(s)}</code>`).join(' ');
          const avoidTags = (t.avoid_periods && t.avoid_periods.length > 0)
            ? t.avoid_periods.map(p => `<kbd>P${p}</kbd>`).join(' ')
            : '<span style="color:var(--text-muted)">None</span>';

          const unavailCount = (t.unavailable || []).length;
          const unavailBadge = unavailCount > 0
            ? `<span class="badge badge-red">${unavailCount} Slots</span>`
            : '<span style="color:var(--text-muted)">Fully Available</span>';

          return `
            <tr>
              <td><strong>${escapeHtml(t.name)}</strong></td>
              <td>${subjectsTags}</td>
              <td><strong>${t.max_load}</strong> hrs/wk</td>
              <td>${avoidTags}</td>
              <td>${unavailBadge}</td>
              <td style="text-align: right;">
                <button type="button" class="btn-table-action" onclick="window.editTeacherItem('${escapeHtml(t.name)}')">Edit</button>
                <button type="button" class="btn-table-action btn-del" onclick="window.deleteTeacherItem('${escapeHtml(t.name)}')">Delete</button>
              </td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

function renderRoomsTable() {
  const rooms = state.customData.rooms || [];
  if (rooms.length === 0) {
    elements.tableRooms.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">No rooms added.</p>`;
    return;
  }

  const typeLabel = {
    lecture_theatre: { text: "Lecture Theatre", cls: "badge-yellow" },
    tutorial_room: { text: "Tutorial Room", cls: "badge-green" },
    classroom: { text: "Classroom", cls: "badge-green" },
    lab: { text: "Laboratory", cls: "badge-blue" }
  };

  elements.tableRooms.innerHTML = `
    <table style="width: 100%;">
      <thead>
        <tr>
          <th>Room Name</th>
          <th>Type</th>
          <th>Capacity</th>
          <th style="text-align: right;">Actions</th>
        </tr>
      </thead>
      <tbody>
        ${rooms.map(r => {
          const normType = (r.type || "classroom").toLowerCase().replace(" ", "_");
          const info = typeLabel[normType] || { text: normType.toUpperCase(), cls: "badge-green" };
          return `
            <tr>
              <td><strong>${escapeHtml(r.name)}</strong></td>
              <td><span class="badge ${info.cls}">${info.text}</span></td>
              <td><strong>${r.capacity}</strong> seats</td>
              <td style="text-align: right;">
                <button type="button" class="btn-table-action" onclick="window.editRoomItem('${escapeHtml(r.name)}')">Edit</button>
                <button type="button" class="btn-table-action btn-del" onclick="window.deleteRoomItem('${escapeHtml(r.name)}')">Delete</button>
              </td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

function renderSubjectsTable() {
  const subjects = state.customData.subjects || [];
  if (subjects.length === 0) {
    elements.tableSubjects.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">No courses added.</p>`;
    return;
  }

  elements.tableSubjects.innerHTML = `
    <table style="width: 100%;">
      <thead>
        <tr>
          <th>Code</th>
          <th>Course Title</th>
          <th>Type</th>
          <th>Weekly Hours</th>
          <th style="text-align: right;">Actions</th>
        </tr>
      </thead>
      <tbody>
        ${subjects.map(s => `
          <tr>
            <td><code style="font-family:var(--font-mono); font-size:0.85rem; font-weight:600;">${escapeHtml(s.code)}</code></td>
            <td><strong>${escapeHtml(s.name)}</strong></td>
            <td><span class="badge ${s.type === 'lab' ? 'badge-blue' : 'badge-green'}">${s.type === 'lab' ? 'Practical Lab' : 'Theory'}</span></td>
            <td>${s.hours} hrs/wk</td>
            <td style="text-align: right;">
              <button type="button" class="btn-table-action" onclick="window.editSubjectItem('${escapeHtml(s.code)}')">Edit</button>
              <button type="button" class="btn-table-action btn-del" onclick="window.deleteSubjectItem('${escapeHtml(s.code)}')">Delete</button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

// =============================================================================
// Modals & Form Handlers
// =============================================================================
function setupModalHandlers() {
  // Close buttons and click outside modal-card
  document.querySelectorAll('.modal-backdrop').forEach(mb => {
    mb.addEventListener('click', (e) => {
      if (e.target === mb) {
        mb.classList.remove('open');
      }
    });
  });

  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      const modalId = btn.getAttribute('data-close');
      const target = document.getElementById(modalId);
      if (target) target.classList.remove('open');
    });
  });

  // Modal open triggers
  if (elements.btnAddBatch) elements.btnAddBatch.addEventListener('click', () => openBatchModal());
  if (elements.btnAddBatchCard) elements.btnAddBatchCard.addEventListener('click', () => openBatchModal());
  if (elements.btnAddTeacher) elements.btnAddTeacher.addEventListener('click', () => openTeacherModal());
  if (elements.btnAddTeacherCard) elements.btnAddTeacherCard.addEventListener('click', () => openTeacherModal());
  if (elements.btnAddRoom) elements.btnAddRoom.addEventListener('click', () => openRoomModal());
  if (elements.btnAddRoomCard) elements.btnAddRoomCard.addEventListener('click', () => openRoomModal());
  if (elements.btnAddSubject) elements.btnAddSubject.addEventListener('click', () => openSubjectModal());
  if (elements.btnAddSubjectCard) elements.btnAddSubjectCard.addEventListener('click', () => openSubjectModal());
  if (elements.btnOpenTimeModal) elements.btnOpenTimeModal.addEventListener('click', () => openTimeModal());
  if (elements.btnQuickEditTime) elements.btnQuickEditTime.addEventListener('click', () => openTimeModal());

  // Form Submissions
  elements.batchForm.addEventListener('submit', handleBatchFormSubmit);
  elements.teacherForm.addEventListener('submit', handleTeacherFormSubmit);
  elements.roomForm.addEventListener('submit', handleRoomFormSubmit);
  elements.subjectForm.addEventListener('submit', handleSubjectFormSubmit);
  elements.timeForm.addEventListener('submit', handleTimeFormSubmit);

  // Batch Form interactive strength and semester controls
  elements.batchSemTypeOdd.addEventListener('change', updateSemesterDropdownOptions);
  elements.batchSemTypeEven.addEventListener('change', updateSemesterDropdownOptions);
  elements.batchStrength.addEventListener('input', updateBatchSplitPreview);

  document.querySelectorAll('.quick-pill[data-strength]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.quick-pill[data-strength]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      elements.batchStrength.value = btn.getAttribute('data-strength');
      updateBatchSplitPreview();
    });
  });

  document.querySelectorAll('.quick-pill[data-room-cap]').forEach(btn => {
    btn.addEventListener('click', () => {
      elements.roomCapacity.value = btn.getAttribute('data-room-cap');
    });
  });

  // Subject Form format toggle
  elements.subjectTypeTheory.addEventListener('change', () => {
    elements.subjectLabBlockGroup.style.display = 'none';
  });
  elements.subjectTypeLab.addEventListener('change', () => {
    elements.subjectLabBlockGroup.style.display = 'block';
  });

  // Time Form periods count change
  elements.timePeriodsCount.addEventListener('change', updateTimeModalPreview);

  // Global window functions for table action buttons
  window.editBatchItem = openBatchModal;
  window.deleteBatchItem = deleteBatchItem;
  window.editTeacherItem = openTeacherModal;
  window.deleteTeacherItem = deleteTeacherItem;
  window.editRoomItem = openRoomModal;
  window.deleteRoomItem = deleteRoomItem;
  window.editSubjectItem = openSubjectModal;
  window.deleteSubjectItem = deleteSubjectItem;
}

// -----------------------------------------------------------------------------
// BATCH MODAL
// -----------------------------------------------------------------------------
function updateSemesterDropdownOptions() {
  const isOdd = elements.batchSemTypeOdd.checked;
  const currentVal = elements.batchSemester.value;
  if (isOdd) {
    elements.batchSemester.innerHTML = `
      <option value="1">Semester 1</option>
      <option value="3">Semester 3</option>
      <option value="5">Semester 5</option>
      <option value="7">Semester 7</option>
    `;
    elements.batchSemester.value = ['1', '3', '5', '7'].includes(currentVal) ? currentVal : '3';
  } else {
    elements.batchSemester.innerHTML = `
      <option value="2">Semester 2</option>
      <option value="4">Semester 4</option>
      <option value="6">Semester 6</option>
      <option value="8">Semester 8</option>
    `;
    elements.batchSemester.value = ['2', '4', '6', '8'].includes(currentVal) ? currentVal : '2';
  }
}

function updateBatchSplitPreview() {
  const strVal = parseInt(elements.batchStrength.value, 10) || 30;
  const nameVal = elements.batchName.value.trim() || 'Cohort';
  const autoSplit = elements.batchAutoSplit.checked;

  if (autoSplit && strVal > 30) {
    const k = Math.ceil(strVal / 30);
    const subNames = Array.from({ length: k }, (_, i) => `${nameVal}${i + 1}`).join(', ');
    elements.batchSplitPreview.style.display = 'block';
    elements.batchSplitPreview.innerHTML = `
      <strong>Lab-Only Sub-Division (Max 30 / Lab Room)</strong>
      <span><strong>Theory lectures</strong>: Full batch of ${strVal} students attends together in a lecture hall.<br>
      <strong>Lab sessions</strong>: Divided into ${k} sub-batches (${escapeHtml(subNames)}) of 30 students each for lab room capacity compliance.</span>
    `;
  } else {
    elements.batchSplitPreview.style.display = 'block';
    elements.batchSplitPreview.innerHTML = `
      <strong>Single Cohort Allocation</strong>
      <span>Batch size is ${strVal}. Will be scheduled as a single unified cohort for all courses.</span>
    `;
  }
}

function openBatchModal(existingName = null) {
  const isEdit = !!existingName;
  document.getElementById('modal-batch-title').textContent = isEdit ? 'Edit Academic Batch' : 'Add Academic Batch';
  elements.batchEditOriginal.value = existingName || '';

  // Populate period slots in lunch dropdown
  const slots = state.customData?.time?.period_slots || [];
  elements.batchLunch.innerHTML = slots.map(s => `
    <option value="${s.period}">Period ${s.period}: ${escapeHtml(s.name)}${s.is_lunch ? ' (Default Lunch)' : ''}</option>
  `).join('');

  // Determine default lunch period based on semester
  // Sem 1 & 2: lunch at period 4 (12:00 PM – 1:00 PM)
  // Sem 3+   : lunch at period 5 (1:00 PM – 2:00 PM)
  const autoLunchForSem = (semNum) => {
    const sem = parseInt(semNum, 10) || 3;
    return (sem === 1 || sem === 2) ? '4' : '5';
  };

  // Populate theory & lab checkboxes
  const subjects = state.customData?.subjects || [];
  const theorySubs = subjects.filter(s => s.type === 'theory');
  const labSubs = subjects.filter(s => s.type === 'lab');

  let batch = null;
  if (isEdit) {
    batch = state.customData.batches.find(b => b.name === existingName);
  }

  elements.batchName.value = batch ? batch.name : '';
  const semType = batch ? (batch.sem_type || 'odd') : 'odd';
  if (semType === 'even') {
    elements.batchSemTypeEven.checked = true;
  } else {
    elements.batchSemTypeOdd.checked = true;
  }
  updateSemesterDropdownOptions();
  if (batch) {
    elements.batchSemester.value = String(batch.semester || '3');
  }

  elements.batchStrength.value = batch ? batch.strength : 120;
  elements.batchAutoSplit.checked = batch ? (batch.auto_split !== false) : true;

  // Set lunch: if editing use stored value; if adding new batch, auto-pick by semester
  if (batch) {
    elements.batchLunch.value = String(batch.lunch_period || 5);
  } else {
    // Auto-select based on currently chosen semester
    const defaultLunch = autoLunchForSem(elements.batchSemester.value);
    elements.batchLunch.value = defaultLunch;
  }

  // Whenever semester changes, auto-update the lunch period for new batches
  elements.batchSemester.onchange = () => {
    if (!elements.batchEditOriginal.value.trim()) {
      elements.batchLunch.value = autoLunchForSem(elements.batchSemester.value);
    }
  };

  const assignedTheory = new Set(batch ? (batch.subjects || []) : []);
  elements.batchTheoryCheckboxes.innerHTML = theorySubs.map(s => {
    const checked = assignedTheory.has(s.code) ? 'checked' : '';
    return `
      <label class="pill-check ${checked ? 'checked' : ''}">
        <input type="checkbox" name="batch-theory" value="${escapeHtml(s.code)}" ${checked}>
        ${escapeHtml(s.code)}: ${escapeHtml(s.name)} (${s.hours}h)
      </label>
    `;
  }).join('') || '<span style="color:var(--text-muted); font-size:0.85rem;">No theory subjects created yet.</span>';

  const assignedLabs = new Set(batch ? (batch.labs || []) : []);
  elements.batchLabCheckboxes.innerHTML = labSubs.map(s => {
    const checked = assignedLabs.has(s.code) ? 'checked' : '';
    return `
      <label class="pill-check ${checked ? 'checked' : ''}">
        <input type="checkbox" name="batch-lab" value="${escapeHtml(s.code)}" ${checked}>
        ${escapeHtml(s.code)}: ${escapeHtml(s.name)} (${s.hours}h Lab)
      </label>
    `;
  }).join('') || '<span style="color:var(--text-muted); font-size:0.85rem;">No lab subjects created yet.</span>';

  // Toggle visual checked class on checkboxes
  document.querySelectorAll('#batch-theory-checkboxes input, #batch-lab-checkboxes input').forEach(chk => {
    chk.addEventListener('change', () => {
      chk.parentElement.classList.toggle('checked', chk.checked);
    });
  });

  updateBatchSplitPreview();
  elements.modalBatch.classList.add('open');
}

function handleBatchFormSubmit(e) {
  e.preventDefault();
  const originalName = elements.batchEditOriginal.value.trim();
  const name = elements.batchName.value.trim();
  const semType = elements.batchSemTypeOdd.checked ? 'odd' : 'even';
  const semester = parseInt(elements.batchSemester.value, 10) || 1;
  const strength = parseInt(elements.batchStrength.value, 10) || 30;
  const autoSplit = elements.batchAutoSplit.checked;
  const lunchPeriod = parseInt(elements.batchLunch.value, 10) || 5;

  const selectedTheory = Array.from(document.querySelectorAll('input[name="batch-theory"]:checked')).map(el => el.value);
  const selectedLabs = Array.from(document.querySelectorAll('input[name="batch-lab"]:checked')).map(el => el.value);

  if (!name) {
    alert('Please enter a batch name.');
    return;
  }

  // Check unique name
  const existingIdx = state.customData.batches.findIndex(b => b.name === name);
  if (originalName) {
    if (existingIdx !== -1 && state.customData.batches[existingIdx].name !== originalName) {
      alert(`A batch with name "${name}" already exists.`);
      return;
    }
  } else {
    if (existingIdx !== -1) {
      alert(`A batch with name "${name}" already exists.`);
      return;
    }
  }

  const batchObj = {
    name,
    semester,
    sem_type: semType,
    strength,
    auto_split: autoSplit,
    lunch_period: lunchPeriod,
    subjects: selectedTheory,
    labs: selectedLabs,
    teacher_map: {}
  };

  if (originalName) {
    const idx = state.customData.batches.findIndex(b => b.name === originalName);
    if (idx !== -1) {
      state.customData.batches[idx] = batchObj;
    } else {
      state.customData.batches.push(batchObj);
    }
  } else {
    state.customData.batches.push(batchObj);
  }

  elements.modalBatch.classList.remove('open');
  applyCustomDataAndUpdateUI(true);
}

function deleteBatchItem(name) {
  if (!confirm(`Are you sure you want to delete batch "${name}"?`)) return;
  state.customData.batches = state.customData.batches.filter(b => b.name !== name);
  applyCustomDataAndUpdateUI(true);
}

// -----------------------------------------------------------------------------
// TEACHER MODAL
// -----------------------------------------------------------------------------
function openTeacherModal(existingName = null) {
  const isEdit = !!existingName;
  document.getElementById('modal-teacher-title').textContent = isEdit ? 'Edit Faculty Member' : 'Add Faculty Member';
  elements.teacherEditOriginal.value = existingName || '';

  let teacher = null;
  if (isEdit) {
    teacher = state.customData.teachers.find(t => t.name === existingName);
  }

  elements.teacherName.value = teacher ? teacher.name : '';
  elements.teacherMaxLoad.value = teacher ? teacher.max_load : 16;

  // Subjects checkboxes
  const allCourses = state.customData.subjects || [];
  const assigned = new Set(teacher ? (teacher.subjects || []) : []);
  elements.teacherSubjectsCheckboxes.innerHTML = allCourses.map(s => {
    const checked = assigned.has(s.code) ? 'checked' : '';
    return `
      <label class="pill-check ${checked ? 'checked' : ''}">
        <input type="checkbox" name="teacher-subj" value="${escapeHtml(s.code)}" ${checked}>
        ${escapeHtml(s.code)} (${s.name})
      </label>
    `;
  }).join('') || '<span style="color:var(--text-muted); font-size:0.85rem;">No subjects created yet.</span>';

  // Avoid periods checkboxes (1..periods_per_day)
  const periodsCount = state.customData.time.periods_per_day || 8;
  const avoided = new Set(teacher ? (teacher.avoid_periods || []) : []);
  elements.teacherAvoidPeriods.innerHTML = Array.from({ length: periodsCount }, (_, i) => {
    const p = i + 1;
    const checked = avoided.has(p) ? 'checked' : '';
    return `
      <label class="pill-check ${checked ? 'checked' : ''}">
        <input type="checkbox" name="teacher-avoid" value="${p}" ${checked}>
        Period ${p}
      </label>
    `;
  }).join('');

  document.querySelectorAll('#teacher-subjects-checkboxes input, #teacher-avoid-periods input').forEach(chk => {
    chk.addEventListener('change', () => {
      chk.parentElement.classList.toggle('checked', chk.checked);
    });
  });

  // Build interactive Unavailable Slots grid
  teacherUnavailSelection = new Set();
  if (teacher && teacher.unavailable) {
    teacher.unavailable.forEach(u => teacherUnavailSelection.add(`${u[0]}_${u[1]}`));
  }
  renderTeacherUnavailGrid();

  elements.modalTeacher.classList.add('open');
}

function renderTeacherUnavailGrid() {
  const days = state.customData.time.days || ["Mon", "Tue", "Wed", "Thu", "Fri"];
  const periodsCount = state.customData.time.periods_per_day || 8;
  const periodSlots = state.customData.time.period_slots || [];

  let html = `<table class="unavail-matrix-table"><thead><tr><th>Day</th>`;
  for (let p = 1; p <= periodsCount; p++) {
    const slot = periodSlots.find(s => s.period === p);
    const label = slot ? slot.name : `P${p}`;
    html += `<th>P${p}<br><span style="font-size:0.65rem; font-weight:normal;">${escapeHtml(label)}</span></th>`;
  }
  html += `</tr></thead><tbody>`;

  days.forEach(d => {
    html += `<tr><td><strong>${escapeHtml(d)}</strong></td>`;
    for (let p = 1; p <= periodsCount; p++) {
      const key = `${d}_${p}`;
      const isUnavail = teacherUnavailSelection.has(key);
      html += `
        <td>
          <button type="button" class="unavail-slot-btn ${isUnavail ? 'is-unavail' : ''}" data-slot="${key}">
            ${isUnavail ? 'OFF' : 'AV'}
          </button>
        </td>
      `;
    }
    html += `</tr>`;
  });
  html += `</tbody></table>`;
  elements.teacherUnavailGridContainer.innerHTML = html;

  // Click handler to toggle unavailable
  elements.teacherUnavailGridContainer.querySelectorAll('.unavail-slot-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const slotKey = btn.getAttribute('data-slot');
      if (teacherUnavailSelection.has(slotKey)) {
        teacherUnavailSelection.delete(slotKey);
        btn.classList.remove('is-unavail');
        btn.textContent = 'AV';
      } else {
        teacherUnavailSelection.add(slotKey);
        btn.classList.add('is-unavail');
        btn.textContent = 'OFF';
      }
    });
  });
}

function handleTeacherFormSubmit(e) {
  e.preventDefault();
  const originalName = elements.teacherEditOriginal.value.trim();
  const name = elements.teacherName.value.trim();
  const maxLoad = parseInt(elements.teacherMaxLoad.value, 10) || 16;

  const selectedSubs = Array.from(document.querySelectorAll('input[name="teacher-subj"]:checked')).map(el => el.value);
  const selectedAvoid = Array.from(document.querySelectorAll('input[name="teacher-avoid"]:checked')).map(el => parseInt(el.value, 10));

  if (!name) {
    alert('Please enter a faculty name.');
    return;
  }

  const existingIdx = state.customData.teachers.findIndex(t => t.name === name);
  if (originalName) {
    if (existingIdx !== -1 && state.customData.teachers[existingIdx].name !== originalName) {
      alert(`A faculty member named "${name}" already exists.`);
      return;
    }
  } else {
    if (existingIdx !== -1) {
      alert(`A faculty member named "${name}" already exists.`);
      return;
    }
  }

  // Parse unavailable slots
  const unavailList = [];
  teacherUnavailSelection.forEach(key => {
    const parts = key.split('_');
    if (parts.length === 2) {
      unavailList.push([parts[0], parseInt(parts[1], 10)]);
    }
  });

  const teacherObj = {
    name,
    subjects: selectedSubs,
    max_load: maxLoad,
    avoid_periods: selectedAvoid,
    unavailable: unavailList
  };

  if (originalName) {
    const idx = state.customData.teachers.findIndex(t => t.name === originalName);
    if (idx !== -1) {
      state.customData.teachers[idx] = teacherObj;
    } else {
      state.customData.teachers.push(teacherObj);
    }
  } else {
    state.customData.teachers.push(teacherObj);
  }

  elements.modalTeacher.classList.remove('open');
  applyCustomDataAndUpdateUI(true);
}

function deleteTeacherItem(name) {
  if (!confirm(`Are you sure you want to remove faculty "${name}"?`)) return;
  state.customData.teachers = state.customData.teachers.filter(t => t.name !== name);
  applyCustomDataAndUpdateUI(true);
}

// -----------------------------------------------------------------------------
// ROOM MODAL
// -----------------------------------------------------------------------------
function openRoomModal(existingName = null) {
  const isEdit = !!existingName;
  document.getElementById('modal-room-title').textContent = isEdit ? 'Edit Room / Facility' : 'Add Room / Facility';
  elements.roomEditOriginal.value = existingName || '';

  let room = null;
  if (isEdit) {
    room = state.customData.rooms.find(r => r.name === existingName);
  }

  elements.roomName.value = room ? room.name : '';
  const rType = room ? (room.type || 'classroom').toLowerCase().replace(' ', '_') : 'classroom';
  elements.roomType.value = rType;
  elements.roomCapacity.value = room ? room.capacity : 60;

  elements.modalRoom.classList.add('open');
}

function handleRoomFormSubmit(e) {
  e.preventDefault();
  const originalName = elements.roomEditOriginal.value.trim();
  const name = elements.roomName.value.trim();
  const type = elements.roomType.value;
  const capacity = parseInt(elements.roomCapacity.value, 10) || 60;

  if (!name) {
    alert('Please enter a room name.');
    return;
  }

  const existingIdx = state.customData.rooms.findIndex(r => r.name === name);
  if (originalName) {
    if (existingIdx !== -1 && state.customData.rooms[existingIdx].name !== originalName) {
      alert(`A room named "${name}" already exists.`);
      return;
    }
  } else {
    if (existingIdx !== -1) {
      alert(`A room named "${name}" already exists.`);
      return;
    }
  }

  const roomObj = { name, type, capacity };

  if (originalName) {
    const idx = state.customData.rooms.findIndex(r => r.name === originalName);
    if (idx !== -1) {
      state.customData.rooms[idx] = roomObj;
    } else {
      state.customData.rooms.push(roomObj);
    }
  } else {
    state.customData.rooms.push(roomObj);
  }

  elements.modalRoom.classList.remove('open');
  applyCustomDataAndUpdateUI(true);
}

function deleteRoomItem(name) {
  if (!confirm(`Are you sure you want to delete room "${name}"?`)) return;
  state.customData.rooms = state.customData.rooms.filter(r => r.name !== name);
  applyCustomDataAndUpdateUI(true);
}

// -----------------------------------------------------------------------------
// SUBJECT / LAB MODAL
// -----------------------------------------------------------------------------
function openSubjectModal(existingCode = null) {
  const isEdit = !!existingCode;
  document.getElementById('modal-subject-title').textContent = isEdit ? 'Edit Course / Subject' : 'Add Course / Subject';
  elements.subjectEditOriginal.value = existingCode || '';

  let subject = null;
  if (isEdit) {
    subject = state.customData.subjects.find(s => s.code === existingCode);
  }

  elements.subjectCode.value = subject ? subject.code : '';
  elements.subjectName.value = subject ? subject.name : '';
  const isLab = subject ? (subject.type === 'lab') : false;
  if (isLab) {
    elements.subjectTypeLab.checked = true;
    elements.subjectLabBlockGroup.style.display = 'block';
  } else {
    elements.subjectTypeTheory.checked = true;
    elements.subjectLabBlockGroup.style.display = 'none';
  }
  elements.subjectHours.value = subject ? subject.hours : 4;
  elements.subjectLabBlock.value = state.customData.time.lab_block || 2;

  elements.modalSubject.classList.add('open');
}

function handleSubjectFormSubmit(e) {
  e.preventDefault();
  const originalCode = elements.subjectEditOriginal.value.trim();
  const code = elements.subjectCode.value.trim().toUpperCase();
  const name = elements.subjectName.value.trim();
  const type = elements.subjectTypeLab.checked ? 'lab' : 'theory';
  const hours = parseInt(elements.subjectHours.value, 10) || 4;

  if (!code || !name) {
    alert('Please provide course code and title.');
    return;
  }

  const existingIdx = state.customData.subjects.findIndex(s => s.code === code);
  if (originalCode) {
    if (existingIdx !== -1 && state.customData.subjects[existingIdx].code !== originalCode) {
      alert(`A course with code "${code}" already exists.`);
      return;
    }
  } else {
    if (existingIdx !== -1) {
      alert(`A course with code "${code}" already exists.`);
      return;
    }
  }

  const subjectObj = { code, name, type, hours };

  if (originalCode) {
    const idx = state.customData.subjects.findIndex(s => s.code === originalCode);
    if (idx !== -1) {
      state.customData.subjects[idx] = subjectObj;
    } else {
      state.customData.subjects.push(subjectObj);
    }
  } else {
    state.customData.subjects.push(subjectObj);
  }

  elements.modalSubject.classList.remove('open');
  applyCustomDataAndUpdateUI(true);
}

function deleteSubjectItem(code) {
  if (!confirm(`Are you sure you want to delete course "${code}"?`)) return;
  state.customData.subjects = state.customData.subjects.filter(s => s.code !== code);
  applyCustomDataAndUpdateUI(true);
}

// -----------------------------------------------------------------------------
// 9-5 TIME & PERIOD STRUCTURE MODAL
// -----------------------------------------------------------------------------
function openTimeModal() {
  const time = state.customData.time || {};
  elements.timePeriodsCount.value = String(time.periods_per_day || 8);

  // Active days pills
  const currentDays = new Set(time.days || ["Mon", "Tue", "Wed", "Thu", "Fri"]);
  elements.timeDaysPills.querySelectorAll('input').forEach(chk => {
    chk.checked = currentDays.has(chk.value);
    chk.parentElement.classList.toggle('checked', chk.checked);
    chk.onchange = () => chk.parentElement.classList.toggle('checked', chk.checked);
  });

  updateTimeModalPreview();
  elements.modalTime.classList.add('open');
}

function updateTimeModalPreview() {
  const pCount = parseInt(elements.timePeriodsCount.value, 10) || 8;
  const currentLunch = parseInt(elements.timeLunchPeriod.value, 10) || 5;

  // Re-generate lunch dropdown options
  elements.timeLunchPeriod.innerHTML = Array.from({ length: pCount }, (_, i) => {
    const p = i + 1;
    const sH = 9 + i;
    const eH = sH + 1;
    const formatHour = (h) => {
      const period = h >= 12 ? 'PM' : 'AM';
      let hour12 = h % 12;
      if (hour12 === 0) hour12 = 12;
      return `${String(hour12).padStart(2, '0')}:00 ${period}`;
    };
    return `<option value="${p}">Period ${p} (${formatHour(sH)} - ${formatHour(eH)})</option>`;
  }).join('');

  elements.timeLunchPeriod.value = (currentLunch <= pCount) ? String(currentLunch) : String(Math.min(5, pCount));

  // Render Preview Tiles
  const selectedLunch = parseInt(elements.timeLunchPeriod.value, 10);
  const slots = generate9to5Slots(pCount, selectedLunch);
  elements.timeSlotsModalPreview.innerHTML = slots.map(s => `
    <div class="time-slot-tile ${s.is_lunch ? 'is-lunch' : ''}">
      <div class="slot-pnum">Period ${s.period}</div>
      <div class="slot-time">${escapeHtml(s.name)}</div>
    </div>
  `).join('');
}

elements.timeLunchPeriod.addEventListener('change', updateTimeModalPreview);

function handleTimeFormSubmit(e) {
  e.preventDefault();
  const periodsCount = parseInt(elements.timePeriodsCount.value, 10) || 8;
  const lunchPeriod = parseInt(elements.timeLunchPeriod.value, 10) || 5;

  const selectedDays = Array.from(elements.timeDaysPills.querySelectorAll('input:checked')).map(el => el.value);
  if (selectedDays.length === 0) {
    alert('Please select at least one teaching day.');
    return;
  }

  const slots = generate9to5Slots(periodsCount, lunchPeriod);

  state.customData.time = {
    days: selectedDays,
    periods_per_day: periodsCount,
    break_periods: [],
    lab_block: 2,
    period_slots: slots
  };

  // Sync batch lunch periods if any batch has lunch > periodsCount
  (state.customData.batches || []).forEach(b => {
    if (b.lunch_period > periodsCount) {
      b.lunch_period = lunchPeriod;
    }
  });

  elements.modalTime.classList.remove('open');
  applyCustomDataAndUpdateUI(true);
}

// =============================================================================
// Standard Preset Loading
// =============================================================================
async function loadPresetDataset(name) {
  try {
    showNotice(`Loading standard ${name} institutional preset...`, 'blue');
    const res = await fetch(`/api/dataset/${name}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw = await res.json();

    // Convert raw to custom format
    const periodSlots = generate9to5Slots(raw.time.periods_per_day, raw.classes[0]?.lunch_period || 4);
    raw.time.period_slots = periodSlots;

    state.customData = {
      time: raw.time,
      subjects: raw.subjects,
      rooms: raw.rooms,
      teachers: raw.teachers,
      batches: raw.classes.map(c => {
        const theorySubs = c.subjects.filter(sc => {
          const sObj = raw.subjects.find(s => s.code === sc);
          return !sObj || sObj.type === 'theory';
        });
        const labSubs = c.subjects.filter(sc => {
          const sObj = raw.subjects.find(s => s.code === sc);
          return sObj && sObj.type === 'lab';
        });
        return {
          name: c.name,
          semester: 1,
          sem_type: 'odd',
          strength: c.strength,
          auto_split: true,
          lunch_period: c.lunch_period,
          subjects: theorySubs,
          labs: labSubs,
          teacher_map: c.teacher_map || {}
        };
      })
    };

    await applyCustomDataAndUpdateUI(true);
  } catch (err) {
    showNotice(`Error loading preset: ${err.message}`, 'red');
  }
}

function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (event) => {
    try {
      const parsed = JSON.parse(event.target.result);
      const valRes = await fetch('/api/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      const valData = await valRes.json();
      if (!valData.valid) {
        showNotice(`Uploaded JSON failed validation:\n${valData.errors.join('; ')}`, 'red');
        return;
      }

      // Ensure period slots
      if (!parsed.time.period_slots) {
        parsed.time.period_slots = generate9to5Slots(parsed.time.periods_per_day, parsed.classes[0]?.lunch_period || 5);
      }

      state.customData = {
        time: parsed.time,
        subjects: parsed.subjects,
        rooms: parsed.rooms,
        teachers: parsed.teachers,
        batches: parsed.classes.map(c => ({
          name: c.name,
          semester: c.semester || 1,
          sem_type: c.sem_type || 'odd',
          strength: c.strength,
          auto_split: true,
          lunch_period: c.lunch_period,
          subjects: c.subjects.filter(sc => {
            const sObj = parsed.subjects.find(s => s.code === sc);
            return !sObj || sObj.type === 'theory';
          }),
          labs: c.subjects.filter(sc => {
            const sObj = parsed.subjects.find(s => s.code === sc);
            return sObj && sObj.type === 'lab';
          }),
          teacher_map: c.teacher_map || {}
        }))
      };

      await applyCustomDataAndUpdateUI(true);
      showNotice('Uploaded JSON configuration successfully imported.', 'green');
    } catch (err) {
      showNotice(`Failed to parse uploaded JSON file: ${err.message}`, 'red');
    }
  };
  reader.readAsText(file);
}

function downloadTemplate() {
  if (!state.currentData) return;
  const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(state.currentData, null, 2));
  const dlAnchor = document.createElement('a');
  dlAnchor.setAttribute('href', dataStr);
  dlAnchor.setAttribute('download', 'institutional_timetable_specification.json');
  document.body.appendChild(dlAnchor);
  dlAnchor.click();
  dlAnchor.remove();
}

function renderFeasibility(checks, allFeasible) {
  elements.feasibilityBadge.textContent = allFeasible ? 'All Checks Passed' : 'Infeasibility Flagged';
  elements.feasibilityBadge.className = allFeasible ? 'badge badge-green' : 'badge badge-red';

  elements.feasibilityGrid.innerHTML = checks.map(c => `
    <div class="bento-card col-4" style="padding: 18px; margin-bottom: 0;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <strong style="font-size: 0.95rem;">${escapeHtml(c.name)}</strong>
        <span class="badge ${c.passed ? 'badge-green' : 'badge-red'}">${c.passed ? 'PASS' : 'FAIL'}</span>
      </div>
      <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 6px;">${escapeHtml(c.rule)}</p>
      <p style="font-size: 0.82rem; font-family: var(--font-mono); margin: 0;">${escapeHtml(c.detail)}</p>
    </div>
  `).join('');
}

// =============================================================================
// Solver Execution
// =============================================================================
async function handleSolveSubmit(e) {
  e.preventDefault();
  if (!state.currentData) {
    showNotice('Please configure an active institutional dataset before running solver.', 'red');
    return;
  }

  const algo = elements.selectAlgo.value;
  const seed = parseInt(elements.inputSeed.value, 10);
  const timeout = parseFloat(elements.inputTimeout.value);

  elements.btnRunSolve.disabled = true;
  elements.btnRunSolve.innerHTML = `<span style="display:inline-block; animation: spin 1s linear infinite;">⟳</span> Solving...`;
  elements.solutionBadge.innerHTML = `<span class="badge badge-yellow">Search Active</span>`;

  try {
    const payload = {
      algo: algo,
      data: state.currentData,
      seed: seed,
      time_limit: timeout,
      node_limit: 500000,
    };

    const res = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail?.errors ? errData.detail.errors.join('; ') : (errData.detail || `HTTP ${res.status}`));
    }

    const sol = await res.json();

    state.sessions = sol.sessions;
    state.asg = sol.asg;
    state.report = sol.report;
    state.history = [];
    updateUndoCount();

    // Update metrics
    elements.metricTime.textContent = `${sol.time_taken}s`;
    elements.metricHard.textContent = sol.report.hard_total;
    elements.metricSoft.textContent = sol.report.soft_total;
    elements.metricWork.textContent = Number(sol.work).toLocaleString();

    if (sol.success && sol.report.hard_total === 0) {
      elements.solutionBadge.innerHTML = `<span class="badge badge-green">Optimal Zero-Clash Solution</span>`;
      showNotice(`Search succeeded in ${sol.time_taken}s with 0 hard clashes!`, 'green');
    } else {
      elements.solutionBadge.innerHTML = `<span class="badge badge-red">Partial Assignment (${sol.report.hard_total} Clashes)</span>`;
      showNotice(`Search completed with ${sol.report.hard_total} hard clashes remaining.`, 'yellow');
    }

    // Render trace chart
    if (sol.trace && sol.trace.length > 1) {
      elements.traceContainer.style.display = 'block';
      renderTraceChart(sol.trace);
    } else {
      elements.traceContainer.style.display = 'none';
    }

    // Switch to Views tab to display generated schedule
    const viewsTabBtn = document.getElementById('nav-views');
    if (viewsTabBtn) viewsTabBtn.click();
  } catch (err) {
    elements.solutionBadge.innerHTML = `<span class="badge badge-red">Search Exception</span>`;
    showNotice(`Solver failure: ${err.message}`, 'red');
  } finally {
    elements.btnRunSolve.disabled = false;
    elements.btnRunSolve.innerHTML = `
      <svg class="icon" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      Execute Search
    `;
  }
}

function renderTraceChart(trace) {
  const maxVal = Math.max(...trace);
  const minVal = Math.min(...trace);
  const pts = trace.map((val, idx) => {
    const x = (idx / (trace.length - 1)) * 600;
    const logVal = Math.log10(Math.max(1, val));
    const logMax = Math.log10(Math.max(10, maxVal));
    const y = 140 - (logVal / logMax) * 120;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  elements.traceChart.innerHTML = `
    <svg viewBox="0 0 600 150" width="100%" height="100%" style="background:#FBFBFA; border:1px solid #EAEAEA; border-radius:4px;">
      <line x1="0" y1="140" x2="600" y2="140" stroke="#EAEAEA" stroke-width="1"/>
      <polyline fill="none" stroke="#111111" stroke-width="2" points="${pts}"/>
      <text x="8" y="18" font-size="10" font-family="var(--font-mono)" fill="#787774">Start Cost: ${trace[0]}</text>
      <text x="500" y="18" font-size="10" font-family="var(--font-mono)" fill="#346538">Final Cost: ${trace[trace.length - 1]}</text>
    </svg>
  `;
}

// =============================================================================
// Timetable Matrix (Views Tab)
// =============================================================================
function updatePerspectiveDropdown() {
  if (!state.currentData) return;
  const kind = state.currentPerspective;
  let items = [];
  if (kind === 'class') {
    items = state.currentData.classes.map(c => c.name);
  } else if (kind === 'teacher') {
    items = state.currentData.teachers.map(t => t.name);
  } else {
    items = state.currentData.rooms.map(r => r.name);
  }

  elements.selectEntity.innerHTML = items.map(it => `
    <option value="${escapeHtml(it)}">${escapeHtml(it)}</option>
  `).join('');

  state.selectedEntity = items[0] || '';
}

function renderTimetableMatrix() {
  if (!state.currentData || Object.keys(state.asg).length === 0) {
    elements.matrixContainer.innerHTML = `
      <p style="color: var(--text-muted); font-size: 0.95rem; padding: 20px;">
        No timetable generated yet. Execute search under the <strong>Algorithmic Search</strong> tab to build schedule matrices.
      </p>
    `;
    elements.diagnosticsList.innerHTML = `<p style="color: var(--text-muted);">No active schedule.</p>`;
    return;
  }

  const data = state.currentData;
  const sessions = state.sessions;
  const asg = state.asg;
  const kind = state.currentPerspective;
  const entity = state.selectedEntity || elements.selectEntity.value;

  elements.osWindowTitle.textContent = `${kind.toUpperCase()} MATRIX: ${entity}`;

  // Find class lunch period if viewing class
  let classLunch = -1;
  if (kind === 'class') {
    const clsObj = data.classes.find(c => c.name === entity);
    if (clsObj) classLunch = clsObj.lunch_period - 1; // 0-indexed
  }

  const breakSet = new Set((data.time.break_periods || []).map(b => b - 1));
  const periodSlots = data.time.period_slots || [];

  // Build grid data structure: periods x days
  const grid = Array.from({ length: data.time.periods_per_day }, () => Array(data.time.days.length).fill(null));

  for (const s of sessions) {
    const val = asg[s.sid];
    if (!val) continue;
    const [d, p, r] = val;

    let match = false;
    if (kind === 'class' && s.cls === entity) match = true;
    if (kind === 'teacher' && s.teacher === entity) match = true;
    if (kind === 'room' && r === entity) match = true;

    if (match) {
      for (let k = 0; k < s.length; k++) {
        const periodIdx = p + k;
        if (periodIdx >= 0 && periodIdx < data.time.periods_per_day) {
          grid[periodIdx][d] = {
            subject: s.subject,
            teacher: s.teacher,
            cls: s.cls,
            room: r,
            kind: s.kind,
            sid: s.sid,
            length: s.length,
            isStart: (k === 0),
          };
        }
      }
    }
  }

  // Generate HTML table with 9-5 time slot subheadings
  // Tracks cells spanned by multi-period blocks (e.g. 2-period lab sessions)
  const skipGrid = Array.from({ length: data.time.periods_per_day }, () => Array(data.time.days.length).fill(false));

  let tableHtml = `<table class="timetable-grid"><thead><tr><th class="period-col">Period & Time</th>`;
  data.time.days.forEach(d => {
    tableHtml += `<th>${escapeHtml(d)}</th>`;
  });
  tableHtml += `</tr></thead><tbody>`;

  for (let p = 0; p < data.time.periods_per_day; p++) {
    const slotObj = periodSlots.find(s => s.period === (p + 1));
    const slotTimeLabel = slotObj ? slotObj.name : `Period ${p + 1}`;

    tableHtml += `
      <tr>
        <td class="period-col" style="font-weight:600; color:var(--text-muted); text-align:center;">
          <div style="font-family:var(--font-mono); font-size:0.8rem; color:var(--text-main);">P${p + 1}</div>
          <div class="period-time-sub">${escapeHtml(slotTimeLabel)}</div>
        </td>
    `;

    if (breakSet.has(p)) {
      tableHtml += `<td colspan="${data.time.days.length}" class="slot-break">Designated Institutional Break · ${escapeHtml(slotTimeLabel)}</td>`;
    } else if (kind === 'class' && p === classLunch) {
      tableHtml += `<td colspan="${data.time.days.length}" class="slot-lunch">Lunch Break (Protected 1-Hour Cohort Slot) · ${escapeHtml(slotTimeLabel)}</td>`;
    } else {
      for (let d = 0; d < data.time.days.length; d++) {
        if (skipGrid[p][d]) {
          // Cell covered by rowspan from a preceding period in this day
          continue;
        }

        const item = grid[p][d];
        if (item) {
          const isLab = item.kind === 'lab';
          const span = (item.isStart && item.length > 1) ? item.length : 1;

          if (span > 1) {
            for (let sp = 1; sp < span; sp++) {
              if (p + sp < data.time.periods_per_day) {
                skipGrid[p + sp][d] = true;
              }
            }
          }

          let subtitle = '';
          if (kind === 'class') subtitle = `${item.teacher} · ${item.room}`;
          else if (kind === 'teacher') subtitle = `${item.cls} · ${item.room}`;
          else subtitle = `${item.cls} · ${item.teacher}`;

          const rowspanAttr = span > 1 ? ` rowspan="${span}"` : '';
          const labBlockClass = (isLab && span > 1) ? 'slot-lab-block' : '';

          tableHtml += `
            <td${rowspanAttr} class="${span > 1 ? 'cell-span-block' : ''}">
              <div class="slot-occupied ${isLab ? 'slot-lab' : ''} ${labBlockClass}">
                <div class="slot-subject">
                  ${escapeHtml(item.subject)}
                  ${span > 1 ? `<span class="consecutive-tag">${span}-Period Lab</span>` : ''}
                </div>
                <div class="slot-meta">${escapeHtml(subtitle)}</div>
              </div>
            </td>
          `;
        } else {
          tableHtml += `<td><span style="color:#D8D8D6; font-size:0.75rem;">&mdash;</span></td>`;
        }
      }
    }
    tableHtml += `</tr>`;
  }
  tableHtml += `</tbody></table>`;
  elements.matrixContainer.innerHTML = tableHtml;

  // Diagnostics messages
  if (state.report && state.report.messages.length > 0) {
    elements.diagnosticsList.innerHTML = state.report.messages.map(m => `
      <div class="notice-box notice-red" style="padding:8px 14px; margin-bottom:8px; font-family:var(--font-mono); font-size:0.82rem;">
        ${escapeHtml(m)}
      </div>
    `).join('');
  } else {
    elements.diagnosticsList.innerHTML = `
      <div class="notice-box notice-green" style="padding:10px 16px;">
        All binary and unary constraints satisfied. Zero active conflict flags.
      </div>
    `;
  }
}

// =============================================================================
// Manual Editor (Calibration Tab)
// =============================================================================
function initManualEditor() {
  if (!state.currentData || state.sessions.length === 0) {
    elements.diffHard.textContent = '--';
    elements.diffSoft.textContent = '--';
    return;
  }

  const data = state.currentData;
  const periodSlots = data.time.period_slots || [];

  // Populate sessions
  elements.editSession.innerHTML = state.sessions.map(s => {
    const curVal = state.asg[s.sid];
    const loc = curVal ? `${data.time.days[curVal[0]]} P${curVal[1] + 1} (${curVal[2]})` : 'Unplaced';
    return `<option value="${s.sid}">${escapeHtml(s.cls)} | ${escapeHtml(s.subject)} #${s.idx} &mdash; ${loc}</option>`;
  }).join('');

  // Populate days
  elements.editDay.innerHTML = data.time.days.map((d, idx) => `
    <option value="${idx}">${escapeHtml(d)}</option>
  `).join('');

  // Populate periods with time names
  elements.editPeriod.innerHTML = Array.from({ length: data.time.periods_per_day }, (_, i) => {
    const p = i + 1;
    const slotObj = periodSlots.find(s => s.period === p);
    const label = slotObj ? `Period ${p} (${slotObj.name})` : `Period ${p}`;
    return `<option value="${i}">${escapeHtml(label)}</option>`;
  }).join('');

  // Populate rooms
  elements.editRoom.innerHTML = data.rooms.map(r => `
    <option value="${escapeHtml(r.name)}">${escapeHtml(r.name)} (${r.capacity} cap, ${r.type})</option>
  `).join('');

  syncEditInputsWithSelectedSession();
  runTrialEvaluation();
}

function syncEditInputsWithSelectedSession() {
  const sid = parseInt(elements.editSession.value, 10);
  const curVal = state.asg[sid];
  if (curVal) {
    elements.editDay.value = curVal[0];
    elements.editPeriod.value = curVal[1];
    elements.editRoom.value = curVal[2];
  }
}

async function runTrialEvaluation() {
  if (!state.currentData || state.sessions.length === 0) return;
  const sid = parseInt(elements.editSession.value, 10);
  const targetDay = parseInt(elements.editDay.value, 10);
  const targetPeriod = parseInt(elements.editPeriod.value, 10);
  const targetRoom = elements.editRoom.value;

  const trialAsg = { ...state.asg, [sid]: [targetDay, targetPeriod, targetRoom] };

  try {
    const res = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data: state.currentData,
        asg: trialAsg,
      }),
    });
    const rep = await res.json();

    const baseHard = state.report ? state.report.hard_total : 0;
    const baseSoft = state.report ? state.report.soft_total : 0;

    const dHard = rep.hard_total - baseHard;
    const dSoft = rep.soft_total - baseSoft;

    elements.diffHard.textContent = (dHard >= 0 ? `+${dHard}` : `${dHard}`);
    elements.diffHard.style.color = dHard > 0 ? 'var(--pastel-red-text)' : 'inherit';

    elements.diffSoft.textContent = (dSoft >= 0 ? `+${dSoft}` : `${dSoft}`);
    elements.diffSoft.style.color = dSoft > 0 ? 'var(--pastel-red-text)' : (dSoft < 0 ? 'var(--pastel-green-text)' : 'inherit');

    if (rep.messages.length > 0) {
      elements.trialConflictAlerts.innerHTML = rep.messages.map(m => `
        <div style="font-size:0.75rem; color:var(--pastel-red-text); margin-bottom:4px; font-family:var(--font-mono);">
          &bull; ${escapeHtml(m)}
        </div>
      `).join('');
    } else {
      elements.trialConflictAlerts.innerHTML = `<span style="font-size:0.75rem; color:var(--pastel-green-text);">Zero conflicts created by trial assignment.</span>`;
    }
  } catch (err) {
    console.error(err);
  }
}

function handleApplyMove() {
  const sid = parseInt(elements.editSession.value, 10);
  const targetDay = parseInt(elements.editDay.value, 10);
  const targetPeriod = parseInt(elements.editPeriod.value, 10);
  const targetRoom = elements.editRoom.value;

  const oldVal = state.asg[sid];
  state.history.push({ sid, oldVal, newVal: [targetDay, targetPeriod, targetRoom] });
  updateUndoCount();

  state.asg[sid] = [targetDay, targetPeriod, targetRoom];

  // Refresh evaluation
  fetch('/api/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: state.currentData, asg: state.asg }),
  }).then(r => r.json()).then(rep => {
    state.report = rep;
    elements.metricHard.textContent = rep.hard_total;
    elements.metricSoft.textContent = rep.soft_total;
    showNotice(`Applied manual placement for session #${sid}.`, 'green');
    initManualEditor();
  });
}

function handleUndoMove() {
  if (state.history.length === 0) return;
  const last = state.history.pop();
  updateUndoCount();

  state.asg[last.sid] = last.oldVal;

  fetch('/api/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: state.currentData, asg: state.asg }),
  }).then(r => r.json()).then(rep => {
    state.report = rep;
    elements.metricHard.textContent = rep.hard_total;
    elements.metricSoft.textContent = rep.soft_total;
    showNotice(`Reverted move on session #${last.sid}.`, 'blue');
    initManualEditor();
  });
}

function updateUndoCount() {
  elements.undoCount.textContent = `(${state.history.length})`;
}

async function handleSuggestSlots() {
  const sid = parseInt(elements.editSession.value, 10);
  try {
    const res = await fetch('/api/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: state.currentData, asg: state.asg, sid }),
    });
    const data = await res.json();
    elements.suggestedContainer.style.display = 'block';

    if (data.suggestions.length === 0) {
      elements.suggestedList.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted);">No conflict-free slots found for this session in current timetable state.</p>`;
    } else {
      elements.suggestedList.innerHTML = data.suggestions.map(s => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid var(--border-light); font-size:0.8rem;">
          <div>
            <strong>${escapeHtml(s.day_name)} P${s.start_period}</strong> in <code>${escapeHtml(s.room)}</code>
            <span style="font-size:0.75rem; color:var(--text-muted); margin-left:6px;">(Soft: ${s.soft_penalty})</span>
          </div>
          <button class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:0.75rem;" onclick="window.applySuggestedSlot(${s.day_idx}, ${s.start_period - 1}, '${escapeHtml(s.room)}')">
            Select
          </button>
        </div>
      `).join('');
    }
  } catch (err) {
    showNotice(`Could not fetch suggestions: ${err.message}`, 'red');
  }
}

window.applySuggestedSlot = function(day, period, room) {
  elements.editDay.value = day;
  elements.editPeriod.value = period;
  elements.editRoom.value = room;
  runTrialEvaluation();
};

// =============================================================================
// Export Dispatcher (Tab 5)
// =============================================================================
function exportCsv() {
  if (!state.currentData || Object.keys(state.asg).length === 0) {
    showNotice('No active timetable assignment to export.', 'yellow');
    return;
  }
  const data = state.currentData;
  const sessions = state.sessions;
  const asg = state.asg;
  const periodSlots = data.time.period_slots || [];

  let csv = 'SessionID,Cohort,Subject,Teacher,Kind,Length,Day,Period,PeriodTime,Room\n';
  sessions.forEach(s => {
    const val = asg[s.sid];
    if (val) {
      const [d, p, r] = val;
      const slotObj = periodSlots.find(sp => sp.period === (p + 1));
      const slotTime = slotObj ? `"${slotObj.name}"` : `""`;
      csv += `${s.sid},"${s.cls}","${s.subject}","${s.teacher}","${s.kind}",${s.length},"${data.time.days[d]}",${p + 1},${slotTime},"${r}"\n`;
    }
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `academic_timetable_export_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportJson() {
  if (!state.currentData) {
    showNotice('No timetable data available to export.', 'yellow');
    return;
  }
  const payload = {
    institution_data: state.currentData,
    assignment: state.asg,
    report: state.report,
    exported_at: new Date().toISOString()
  };
  const str = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(payload, null, 2));
  const a = document.createElement('a');
  a.href = str;
  a.download = `full_schedule_payload_${Date.now()}.json`;
  a.click();
}

function handlePrintMatrix() {
  window.print();
}

// =============================================================================
// Empirical Benchmarks (Tab 6)
// =============================================================================
async function loadBenchmarks() {
  try {
    const res = await fetch('/api/benchmarks');
    if (!res.ok) return;
    const data = await res.json();
    if (!data.summary || data.summary.length === 0) return;

    const smallRows = data.summary.filter(r => r.Dataset && r.Dataset.toLowerCase().includes('small'));
    const largeRows = data.summary.filter(r => r.Dataset && r.Dataset.toLowerCase().includes('large'));

    let html = `
      <div style="margin-bottom: 24px;">
        <h4 style="font-family: var(--font-serif); font-size: 1.3rem; margin-bottom: 8px;">Small Dataset Benchmark (3 Classes, 6 Faculty, 4 Rooms)</h4>
        ${renderBenchmarkTable(smallRows)}
      </div>
      <div>
        <h4 style="font-family: var(--font-serif); font-size: 1.3rem; margin-bottom: 8px;">Large Dataset Benchmark (8 Classes, 15 Faculty, 8 Rooms)</h4>
        ${renderBenchmarkTable(largeRows)}
      </div>
    `;
    elements.benchmarkContainer.innerHTML = html;
  } catch (err) {
    console.error(err);
  }
}

function renderBenchmarkTable(rows) {
  if (rows.length === 0) return '<p style="color:var(--text-muted);">No benchmark records.</p>';
  return `
    <table style="width:100%; margin-bottom:20px;">
      <thead>
        <tr>
          <th>Algorithmic Method</th>
          <th>Success Rate</th>
          <th>Avg Time (s)</th>
          <th>Std Dev (s)</th>
          <th>Work (Nodes/Iters)</th>
          <th>Avg Hard Clashes</th>
          <th>Avg Soft Penalty</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>
            <td><strong>${escapeHtml(r.Method)}</strong></td>
            <td><span class="badge ${r['Success Rate'].startsWith('10') ? 'badge-green' : 'badge-yellow'}">${r['Success Rate']}</span></td>
            <td>${r['Avg Time (s)']}s</td>
            <td>±${r['Std Time (s)']}s</td>
            <td>${Number(r['Avg Work (nodes/iters)']).toLocaleString()}</td>
            <td>${r['Avg Hard Violations']}</td>
            <td><strong>${r['Avg Soft Penalty (valid runs)']}</strong></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

// =============================================================================
// Utilities
// =============================================================================
function showNotice(msg, type = 'blue') {
  elements.globalNotice.innerHTML = `
    <div class="notice-box notice-${type}">
      ${escapeHtml(msg)}
    </div>
  `;
  setTimeout(() => {
    if (elements.globalNotice.innerHTML.includes(escapeHtml(msg))) {
      elements.globalNotice.innerHTML = '';
    }
  }, 8000);
}

function escapeHtml(str) {
  if (typeof str !== 'string') return str;
  return str.replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;',
  }[tag] || tag));
}
