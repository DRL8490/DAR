import os, re, subprocess

dash_candidates = [p for p in ("templates/mti_dashboard.html", "mti_dashboard.html") if os.path.exists(p)]
if not dash_candidates:
    raise SystemExit("templates/mti_dashboard.html not found! Run inside your DAR project folder.")

ledger_filter_ui_and_js = r"""                <!-- MTI_LEDGER_FILTER_START -->
                <div id="mtiLedgerFilterBar" class="px-3 py-2 border-bottom bg-light">
                    <div class="d-flex flex-wrap align-items-center gap-1">
                        <select id="fltMattXing" class="form-select form-select-sm fw-semibold border-secondary-subtle" style="flex: 1 1 150px; font-size: 11.5px; padding: 3px 24px 3px 7px;" onchange="window.applyMtiLedgerFilters()" title="Filter by Crossing Group (6 Groups: A1 L1+L2, B1 L1+L2, A2, B2, A3, B3)">
                            <option value="ALL">All 6 Crossings</option>
                        </select>
                        <select id="fltMattDate" class="form-select form-select-sm fw-semibold border-secondary-subtle" style="flex: 1 1 115px; font-size: 11.5px; padding: 3px 24px 3px 7px;" onchange="window.applyMtiLedgerFilters()" title="Filter by Installation Date">
                            <option value="ALL">All Dates</option>
                        </select>
                        <select id="fltMattSurv" class="form-select form-select-sm fw-semibold border-secondary-subtle" style="flex: 1 1 128px; font-size: 11.5px; padding: 3px 24px 3px 7px;" onchange="window.applyMtiLedgerFilters()" title="Filter by Recorded Surveyor">
                            <option value="ALL">All Surveyors</option>
                        </select>
                        <select id="fltMattStatus" class="form-select form-select-sm fw-semibold border-secondary-subtle" style="flex: 1 1 132px; font-size: 11.5px; padding: 3px 24px 3px 7px;" onchange="window.applyMtiLedgerFilters()" title="Filter by Status or Tolerance">
                            <option value="ALL">All Status / QA-QC</option>
                        </select>
                        <button type="button" id="btnResetMattFilter" class="btn btn-sm btn-outline-secondary fw-bold px-2 py-0" style="height: 26px; font-size: 11px; display: none;" onclick="window.resetMtiLedgerFilters()" title="Clear all mattress filters">
                            <i class="fas fa-times me-1"></i>Reset
                        </button>
                    </div>
                    <div id="mtiMattFilterStatusRow" class="justify-content-between align-items-center mt-1 px-1" style="display: none; font-size: 11px;">
                        <span id="lblMattFilterSummary" class="fw-bold text-success"></span>
                    </div>
                </div>
                <div id="mtiLedgerEmptyFilterMsg" class="p-3 text-center text-muted small border-bottom bg-white" style="display: none;">
                    No logged mattresses match the selected filter criteria.
                </div>
                <script>
                (function() {
                    const STORAGE_KEY = 'mti_matt_ledger_filters_v1';
                    const SIX_GROUPS = [
                        { key: 'CR-A1', label: 'CR-A1 (L1 & L2)' },
                        { key: 'CR-B1', label: 'CR-B1 (L1 & L2)' },
                        { key: 'CR-A2', label: 'CR-A2' },
                        { key: 'CR-B2', label: 'CR-B2' },
                        { key: 'CR-A3', label: 'CR-A3' },
                        { key: 'CR-B3', label: 'CR-B3' }
                    ];

                    function normMattressGroup(raw) {
                        const s = String(raw || '').trim().toUpperCase();
                        if (!s) return '';
                        const m = s.match(/(?<![#A-Z0-9])(?:CR[-_\s]*([AB][123])|C[-_\s]+([AB][123])|([AB][123])[-_\s]*(?:L[12]|M\d+))(?:\b|[-_\s]|L[12]|M\d)/);
                        if (m) return 'CR-' + (m[1] || m[2] || m[3]);
                        if (/^[AB][123]$/.test(s)) return 'CR-' + s;
                        return '';
                    }

                    function normSurveyorLabel(raw) {
                        const s = String(raw || '').trim();
                        if (!s || s.toLowerCase() === 'duty surveyor' || s.toLowerCase() === 'surveyor') return '';
                        const low = s.toLowerCase();
                        if (low.indexOf('roderick') !== -1 || low.indexOf('clavel') !== -1) return 'Roderick Clavel';
                        if (low.indexOf('abror') !== -1 || low.indexOf('hediarto') !== -1) return 'Mohamad Abror Hediarto';
                        if (low.indexOf('daryll') !== -1 || low.indexOf('enano') !== -1) return 'Daryll Enano';
                        if (low.indexOf('danilo') !== -1 || low.indexOf('bartolome') !== -1) return 'Danilo Bartolome';
                        if (low.indexOf('mateo') !== -1 || low.indexOf('mollaneda') !== -1) return 'Mateo Mollaneda';
                        if (low.indexOf('renante') !== -1 || low.indexOf('bacalan') !== -1) return 'Renante Bacalan';
                        return s;
                    }

                    function getLedgerTableBody() {
                        const bar = document.getElementById('mtiLedgerFilterBar');
                        if (bar && bar.parentElement) {
                            const tb = bar.parentElement.querySelector('table tbody');
                            if (tb) return tb;
                        }
                        const editBtn = document.querySelector('button[onclick*="editFixRow"]');
                        return editBtn ? editBtn.closest('tbody') : null;
                    }

                    function buildLogSurveyorFallbackMap() {
                        const map = {};
                        document.querySelectorAll('button[onclick*="editEventLogRow"]').forEach(btn => {
                            const ds = btn.dataset || {};
                            if (String(ds.type || '').toLowerCase() === 'mattress fix' && ds.ref && ds.surv) {
                                const mBox = String(ds.ref).toUpperCase().match(/CR-[AB][123](?:_L[12])?_M\d+/);
                                if (mBox && !map[mBox[0]]) {
                                    map[mBox[0]] = normSurveyorLabel(ds.surv);
                                }
                            }
                        });
                        return map;
                    }

                    function extractRowMeta(tr, jsonMapByBox, jsonMapById, logSurvMap) {
                        const editBtn = tr.querySelector('button[onclick*="editFixRow"]');
                        const ds = editBtn ? (editBtn.dataset || {}) : {};
                        const rowId = String(ds.id || '').trim();
                        const boxId = String(ds.box || '').trim().toUpperCase();
                        const jRow = (rowId && jsonMapById[rowId]) || (boxId && jsonMapByBox[boxId]) || {};

                        const xingGrp = normMattressGroup(ds.crossing || jRow.crossing_id || boxId || tr.textContent) || 'CR-A1';
                        const dtRaw = String(ds.date || jRow.install_date || tr.textContent || '').trim();
                        const dtYmd = (dtRaw.match(/(\d{4}-\d{2}-\d{2})/) || [null, ''])[1] || 'Unknown';

                        const surv = normSurveyorLabel(ds.surveyor || jRow.surveyor_name || jRow.surveyor || (boxId ? logSurvMap[boxId] : '')) || 'Unassigned';
                        const status = String(ds.status || jRow.status || 'Completed').trim() || 'Completed';

                        const clTol = Number(window.MTI_CL_TOL || 0.50) || 0.50;
                        const gapTol = Number(window.MTI_GAP_TOL || 0.50) || 0.50;
                        const clVal = parseFloat(ds.cl ?? jRow.cl_offset_m ?? '0') || 0.0;
                        const isFirst = (ds.first === 'true') || Boolean(jRow.is_first_in_array);
                        const gapCandidates = [ds.gnw, ds.gne, ds.gsw, ds.gse, ds.gap1, ds.gap2, jRow.gap_m]
                            .map(v => parseFloat(v))
                            .filter(v => !isNaN(v));
                        const maxGap = gapCandidates.length ? Math.max(...gapCandidates) : 0.0;
                        const passTol = (clVal <= clTol) && (isFirst || maxGap <= gapTol);

                        return { xingGrp, dtYmd, surv, status, passTol };
                    }

                    window.initMtiLedgerFilters = function() {
                        const tbody = getLedgerTableBody();
                        if (!tbody) return;
                        const rows = Array.from(tbody.querySelectorAll('tr')).filter(tr => tr.cells && tr.cells.length >= 4);

                        const jsonMapByBox = {}, jsonMapById = {};
                        (window.LEDGER_FIX_ROWS || []).forEach(r => {
                            if (r && r.id !== undefined) jsonMapById[String(r.id)] = r;
                            if (r && r.design_box_id) jsonMapByBox[String(r.design_box_id).toUpperCase()] = r;
                        });
                        const logSurvMap = buildLogSurveyorFallbackMap();

                        const xingCounts = { 'CR-A1': 0, 'CR-B1': 0, 'CR-A2': 0, 'CR-B2': 0, 'CR-A3': 0, 'CR-B3': 0 };
                        const dateCounts = {}, survCounts = {}, statusCounts = {};
                        let passCnt = 0, advCnt = 0;

                        rows.forEach(tr => {
                            const m = extractRowMeta(tr, jsonMapByBox, jsonMapById, logSurvMap);
                            tr.dataset.mfltXing = m.xingGrp;
                            tr.dataset.mfltDate = m.dtYmd;
                            tr.dataset.mfltSurv = m.surv;
                            tr.dataset.mfltStatus = m.status;
                            tr.dataset.mfltTol = m.passTol ? 'PASS' : 'ADV';

                            if (xingCounts[m.xingGrp] !== undefined) xingCounts[m.xingGrp] += 1;
                            if (m.dtYmd && m.dtYmd !== 'Unknown') dateCounts[m.dtYmd] = (dateCounts[m.dtYmd] || 0) + 1;
                            if (m.surv && m.surv !== 'Unassigned') survCounts[m.surv] = (survCounts[m.surv] || 0) + 1;
                            statusCounts[m.status] = (statusCounts[m.status] || 0) + 1;
                            if (m.passTol) passCnt += 1; else advCnt += 1;
                        });

                        const total = rows.length;

                        const selXing = document.getElementById('fltMattXing');
                        if (selXing) {
                            const prevX = selXing.value || 'ALL';
                            selXing.innerHTML = '';
                            selXing.appendChild(new Option(`All 6 Crossings (${total})`, 'ALL'));
                            SIX_GROUPS.forEach(g => {
                                selXing.appendChild(new Option(`${g.label} (${xingCounts[g.key] || 0})`, g.key));
                            });
                            if (Array.from(selXing.options).some(o => o.value === prevX)) selXing.value = prevX;
                        }

                        const selDate = document.getElementById('fltMattDate');
                        if (selDate) {
                            const prevD = selDate.value || 'ALL';
                            const sortedDates = Object.keys(dateCounts).sort().reverse();
                            selDate.innerHTML = '';
                            selDate.appendChild(new Option(`All Dates (${sortedDates.length})`, 'ALL'));
                            sortedDates.forEach(d => selDate.appendChild(new Option(`${d} (${dateCounts[d]})`, d)));
                            if (Array.from(selDate.options).some(o => o.value === prevD)) selDate.value = prevD;
                        }

                        const selSurv = document.getElementById('fltMattSurv');
                        if (selSurv) {
                            const prevS = selSurv.value || 'ALL';
                            const sortedSurvs = Object.keys(survCounts).sort();
                            selSurv.innerHTML = '';
                            selSurv.appendChild(new Option('All Surveyors', 'ALL'));
                            sortedSurvs.forEach(s => selSurv.appendChild(new Option(`${s} (${survCounts[s]})`, s)));
                            if (Array.from(selSurv.options).some(o => o.value === prevS)) selSurv.value = prevS;
                        }

                        const selSt = document.getElementById('fltMattStatus');
                        if (selSt) {
                            const prevSt = selSt.value || 'ALL';
                            selSt.innerHTML = '';
                            selSt.appendChild(new Option(`All Status / QA-QC (${total})`, 'ALL'));
                            if (total > 0) {
                                selSt.appendChild(new Option(`Within Tol <=0.50m (${passCnt})`, '__PASS__'));
                                selSt.appendChild(new Option(`Exceeds Tol >0.50m (${advCnt})`, '__ADV__'));
                            }
                            ['Completed', 'In Progress', 'Planned'].forEach(stKey => {
                                if (statusCounts[stKey]) {
                                    selSt.appendChild(new Option(`${stKey} (${statusCounts[stKey]})`, stKey));
                                }
                            });
                            if (Array.from(selSt.options).some(o => o.value === prevSt)) selSt.value = prevSt;
                        }

                        try {
                            const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
                            ['fltMattXing', 'fltMattDate', 'fltMattSurv', 'fltMattStatus'].forEach(id => {
                                const el = document.getElementById(id);
                                if (el && saved[id] && Array.from(el.options).some(o => o.value === saved[id])) {
                                    el.value = saved[id];
                                }
                            });
                        } catch (e) {}

                        window.applyMtiLedgerFilters();
                    };

                    window.applyMtiLedgerFilters = function() {
                        const tbody = getLedgerTableBody();
                        if (!tbody) return;
                        const rows = Array.from(tbody.querySelectorAll('tr')).filter(tr => tr.cells && tr.cells.length >= 4);
                        const vXing = document.getElementById('fltMattXing')?.value || 'ALL';
                        const vDate = document.getElementById('fltMattDate')?.value || 'ALL';
                        const vSurv = document.getElementById('fltMattSurv')?.value || 'ALL';
                        const vSt = document.getElementById('fltMattStatus')?.value || 'ALL';

                        try {
                            sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
                                fltMattXing: vXing, fltMattDate: vDate, fltMattSurv: vSurv, fltMattStatus: vSt
                            }));
                        } catch (e) {}

                        let shown = 0;
                        rows.forEach(tr => {
                            const okXing = (vXing === 'ALL') || (tr.dataset.mfltXing === vXing);
                            const okDate = (vDate === 'ALL') || (tr.dataset.mfltDate === vDate);
                            const okSurv = (vSurv === 'ALL') || (tr.dataset.mfltSurv === vSurv);
                            const okSt = (vSt === 'ALL')
                                ? true
                                : ((vSt === '__PASS__') ? (tr.dataset.mfltTol === 'PASS')
                                : ((vSt === '__ADV__') ? (tr.dataset.mfltTol === 'ADV')
                                : (tr.dataset.mfltStatus === vSt)));
                            const vis = okXing && okDate && okSurv && okSt;
                            tr.style.display = vis ? '' : 'none';
                            if (vis) shown += 1;
                        });

                        const isFiltered = (vXing !== 'ALL' || vDate !== 'ALL' || vSurv !== 'ALL' || vSt !== 'ALL');
                        const resetBtn = document.getElementById('btnResetMattFilter');
                        if (resetBtn) resetBtn.style.display = isFiltered ? 'inline-block' : 'none';

                        const statusRow = document.getElementById('mtiMattFilterStatusRow');
                        const summaryLbl = document.getElementById('lblMattFilterSummary');
                        if (statusRow && summaryLbl) {
                            statusRow.style.display = isFiltered ? 'flex' : 'none';
                            summaryLbl.textContent = `Showing ${shown} of ${rows.length} Logged Mattresses`;
                        }

                        const emptyMsg = document.getElementById('mtiLedgerEmptyFilterMsg');
                        if (emptyMsg) emptyMsg.style.display = (rows.length > 0 && shown === 0) ? 'block' : 'none';
                    };

                    window.resetMtiLedgerFilters = function() {
                        ['fltMattXing', 'fltMattDate', 'fltMattSurv', 'fltMattStatus'].forEach(id => {
                            const el = document.getElementById(id);
                            if (el) el.value = 'ALL';
                        });
                        window.applyMtiLedgerFilters();
                    };

                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', window.initMtiLedgerFilters);
                    } else {
                        window.initMtiLedgerFilters();
                    }
                })();
                </script>
                <!-- MTI_LEDGER_FILTER_END -->"""

for dash_path in dash_candidates:
    dh = open(dash_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    if "<!-- MTI_LEDGER_FILTER_START -->" in dh:
        dh_new, n_rep = re.subn(
            r"[ \t]*<!-- MTI_LEDGER_FILTER_START -->.*?<!-- MTI_LEDGER_FILTER_END -->",
            lambda _m: ledger_filter_ui_and_js,
            dh, count=1, flags=re.S
        )
    else:
        dh_new, n_rep = re.subn(
            r"([ \t]*<!-- EXACT 6 REQUESTED COLUMNS[^\n]*-->)",
            lambda m: ledger_filter_ui_and_js + "\n\n" + m.group(1),
            dh, count=1
        )
        if not n_rep:
            idx_drw = dh.find('id="addFixDrawer"')
            if idx_drw != -1:
                m_cb = re.search(r'([ \t]*<div class="card-body p-0">)', dh[idx_drw:])
                if m_cb:
                    ins_at = idx_drw + m_cb.start(1)
                    dh_new = dh[:ins_at] + ledger_filter_ui_and_js + "\n" + dh[ins_at:]
                    n_rep = 1
    if not n_rep:
        raise SystemExit(f"Could not locate Mattress Fix Ledger table anchor in {dash_path}!")

    open(dash_path, "w", encoding="utf-8").write(dh_new)
    print(f"  -> Updated {dash_path} (Added 6-Crossing-Group, Date, Surveyor & Status/QA-QC filter bar above Logged Mattress Ledger)")

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-ui): add 6-crossing-group dropdown filter bar for Logged Mattress Ledger"], check=False)
print("\nLOGGED MATTRESS LEDGER DROPDOWN FILTER COMPLETE & SYNCED!")