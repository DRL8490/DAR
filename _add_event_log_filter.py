import os, re, subprocess

dash_candidates = [p for p in ("templates/mti_dashboard.html", "mti_dashboard.html") if os.path.exists(p)]
if not dash_candidates:
    raise SystemExit("templates/mti_dashboard.html not found! Run inside your DAR project folder.")

filter_ui_and_js = r"""                    <!-- MTI_EVENT_LOG_FILTER_START -->
                    <div id="mtiEventLogFilterBar" class="p-2 mb-2 rounded border bg-light">
                        <div class="d-flex flex-wrap align-items-center gap-1">
                            <select id="fltLogType" class="form-select form-select-sm fw-semibold border-secondary-subtle" style="flex: 1 1 142px; font-size: 11.5px; padding: 3px 24px 3px 7px;" onchange="window.applyMtiEventLogFilters()" title="Filter by Event Category">
                                <option value="ALL">All Event Types</option>
                            </select>
                            <select id="fltLogDate" class="form-select form-select-sm fw-semibold border-secondary-subtle" style="flex: 1 1 112px; font-size: 11.5px; padding: 3px 24px 3px 7px;" onchange="window.applyMtiEventLogFilters()" title="Filter by Log Date">
                                <option value="ALL">All Dates</option>
                            </select>
                            <select id="fltLogXing" class="form-select form-select-sm fw-semibold border-secondary-subtle" style="flex: 1 1 104px; font-size: 11.5px; padding: 3px 24px 3px 7px;" onchange="window.applyMtiEventLogFilters()" title="Filter by Crossing Group">
                                <option value="ALL">All Crossings</option>
                            </select>
                            <select id="fltLogSurv" class="form-select form-select-sm fw-semibold border-secondary-subtle" style="flex: 1 1 118px; font-size: 11.5px; padding: 3px 24px 3px 7px;" onchange="window.applyMtiEventLogFilters()" title="Filter by Surveyor">
                                <option value="ALL">All Surveyors</option>
                            </select>
                            <button type="button" id="btnResetLogFilter" class="btn btn-sm btn-outline-secondary fw-bold px-2 py-0" style="height: 26px; font-size: 11px; display: none;" onclick="window.resetMtiEventLogFilters()" title="Clear all log filters">
                                <i class="fas fa-times me-1"></i>Reset
                            </button>
                        </div>
                        <div id="mtiLogFilterStatusRow" class="justify-content-between align-items-center mt-1 px-1" style="display: none; font-size: 11px;">
                            <span id="lblLogFilterSummary" class="fw-bold text-primary"></span>
                        </div>
                    </div>
                    <div id="mtiLogEmptyFilterMsg" class="p-3 mb-2 text-center text-muted small border rounded bg-white" style="display: none;">
                        No survey input logs match the selected filter criteria.
                    </div>
                    <script>
                    (function() {
                        const STORAGE_KEY = 'mti_evt_log_filters_v1';

                        function normCrossingGroup(raw) {
                            const s = String(raw || '').toUpperCase();
                            const m = s.match(/(?<![#A-Z0-9])(?:CR[-_\s]?([AB][123])|C[-_]([AB][123])|([AB][123])[-_](?:L[12]|M\d+))(?:\b|[_-]|M\d)/);
                            if (m) return 'C-' + (m[1] || m[2] || m[3]);
                            return 'OTHER';
                        }

                        function normSurveyorLabel(raw) {
                            const s = String(raw || '').trim();
                            if (!s) return 'Unknown';
                            const low = s.toLowerCase();
                            if (low.indexOf('roderick') !== -1 || low.indexOf('clavel') !== -1) return 'Roderick Clavel';
                            if (low.indexOf('abror') !== -1 || low.indexOf('hediarto') !== -1) return 'Mohamad Abror Hediarto';
                            if (low.indexOf('daryll') !== -1 || low.indexOf('enano') !== -1) return 'Daryll Enano';
                            if (low.indexOf('danilo') !== -1 || low.indexOf('bartolome') !== -1) return 'Danilo Bartolome';
                            if (low.indexOf('mateo') !== -1 || low.indexOf('mollaneda') !== -1) return 'Mateo Mollaneda';
                            if (low.indexOf('renante') !== -1 || low.indexOf('bacalan') !== -1) return 'Renante Bacalan';
                            return s;
                        }

                        function normEventType(raw) {
                            const s = String(raw || '').trim();
                            if (s.toLowerCase() === 'survey issue') return 'Survey Issue Reporting';
                            return s || 'Other';
                        }

                        function getStreamContainer() {
                            const bar = document.getElementById('mtiEventLogFilterBar');
                            if (!bar) return null;
                            let el = bar.nextElementSibling;
                            while (el) {
                                if (el.tagName === 'DIV' && el.id !== 'mtiLogEmptyFilterMsg' && (el.style.overflowY === 'auto' || el.querySelector('button[onclick*="editEventLogRow"]'))) {
                                    return el;
                                }
                                el = el.nextElementSibling;
                            }
                            return null;
                        }

                        function extractCardMeta(card) {
                            const editBtn = card.querySelector('button[onclick*="editEventLogRow"]');
                            const ds = editBtn ? editBtn.dataset : {};
                            const badges = card.querySelectorAll('.badge');
                            const evtType = normEventType(ds.type || (badges[0] ? badges[0].textContent : ''));
                            const tsRaw = (ds.ts || (card.querySelector('strong.mono') ? card.querySelector('strong.mono').textContent : '') || '').trim();
                            const dtYmd = (tsRaw.match(/^(\d{4}-\d{2}-\d{2})/) || [null, ''])[1] || 'Unknown';
                            const survEl = card.querySelector('.text-nowrap small.text-muted');
                            const surv = normSurveyorLabel(ds.surv || (survEl ? survEl.textContent : ''));
                            const refStr = (ds.ref || '') + ' ' + (card.textContent || '');
                            const xingGrp = normCrossingGroup(refStr);
                            const isKpi = (ds.kpi === 'true') || (evtType.toLowerCase() === 'mattress fix') || Array.from(badges).some(b => b.textContent.trim() === 'KPI');
                            return { evtType, dtYmd, surv, xingGrp, isKpi };
                        }

                        function populateSelect(selEl, allLabel, countsMap, orderedKeys, extraTopOptions) {
                            if (!selEl) return;
                            const prev = selEl.value || 'ALL';
                            selEl.innerHTML = '';
                            selEl.appendChild(new Option(allLabel, 'ALL'));
                            (extraTopOptions || []).forEach(opt => {
                                selEl.appendChild(new Option(opt.label, opt.value));
                            });
                            orderedKeys.forEach(k => {
                                if (countsMap[k]) {
                                    const disp = (k === 'OTHER') ? 'Vessel / General' : k;
                                    selEl.appendChild(new Option(`${disp} (${countsMap[k]})`, k));
                                }
                            });
                            if (Array.from(selEl.options).some(o => o.value === prev)) {
                                selEl.value = prev;
                            }
                        }

                        window.initMtiEventLogFilters = function() {
                            const stream = getStreamContainer();
                            if (!stream) return;
                            const cards = Array.from(stream.children).filter(el => el.tagName === 'DIV');
                            const typeCounts = {}, dateCounts = {}, xingCounts = {}, survCounts = {};
                            let kpiCount = 0;

                            cards.forEach(card => {
                                const m = extractCardMeta(card);
                                card.dataset.fltType = m.evtType;
                                card.dataset.fltDate = m.dtYmd;
                                card.dataset.fltXing = m.xingGrp;
                                card.dataset.fltSurv = m.surv;
                                card.dataset.fltKpi = m.isKpi ? '1' : '0';

                                typeCounts[m.evtType] = (typeCounts[m.evtType] || 0) + 1;
                                if (m.dtYmd && m.dtYmd !== 'Unknown') dateCounts[m.dtYmd] = (dateCounts[m.dtYmd] || 0) + 1;
                                xingCounts[m.xingGrp] = (xingCounts[m.xingGrp] || 0) + 1;
                                if (m.surv && m.surv !== 'Unknown') survCounts[m.surv] = (survCounts[m.surv] || 0) + 1;
                                if (m.isKpi) kpiCount += 1;
                            });

                            const total = cards.length;
                            const prefTypeOrder = ['Mattress fix', 'Mattress on water', 'Frame above water', 'ROV & Vessel Ops', 'Calib, Setup & TBT', 'Survey Issue Reporting', 'Pole down', 'Pole up'];
                            const allTypes = Array.from(new Set([...prefTypeOrder.filter(k => typeCounts[k]), ...Object.keys(typeCounts).sort()]));
                            const allDates = Object.keys(dateCounts).sort().reverse();
                            const prefXings = ['C-A1', 'C-B1', 'C-A2', 'C-B2', 'C-A3', 'C-B3', 'OTHER'];
                            const allXings = prefXings.filter(k => xingCounts[k]);
                            const allSurvs = Object.keys(survCounts).sort();

                            const extraKpi = kpiCount > 0 ? [{ label: `KPI Synced Only (${kpiCount})`, value: '__KPI__' }] : [];
                            populateSelect(document.getElementById('fltLogType'), `All Event Types (${total})`, typeCounts, allTypes, extraKpi);
                            populateSelect(document.getElementById('fltLogDate'), `All Dates (${allDates.length})`, dateCounts, allDates);
                            populateSelect(document.getElementById('fltLogXing'), 'All Crossings', xingCounts, allXings);
                            populateSelect(document.getElementById('fltLogSurv'), 'All Surveyors', survCounts, allSurvs);

                            try {
                                const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
                                ['fltLogType', 'fltLogDate', 'fltLogXing', 'fltLogSurv'].forEach(id => {
                                    const el = document.getElementById(id);
                                    if (el && saved[id] && Array.from(el.options).some(o => o.value === saved[id])) {
                                        el.value = saved[id];
                                    }
                                });
                            } catch (e) {}

                            window.applyMtiEventLogFilters();
                        };

                        window.applyMtiEventLogFilters = function() {
                            const stream = getStreamContainer();
                            if (!stream) return;
                            const cards = Array.from(stream.children).filter(el => el.tagName === 'DIV');
                            const vType = document.getElementById('fltLogType')?.value || 'ALL';
                            const vDate = document.getElementById('fltLogDate')?.value || 'ALL';
                            const vXing = document.getElementById('fltLogXing')?.value || 'ALL';
                            const vSurv = document.getElementById('fltLogSurv')?.value || 'ALL';

                            try {
                                sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ fltLogType: vType, fltLogDate: vDate, fltLogXing: vXing, fltLogSurv: vSurv }));
                            } catch (e) {}

                            let shown = 0;
                            cards.forEach(card => {
                                const okType = (vType === 'ALL') ? true : ((vType === '__KPI__') ? (card.dataset.fltKpi === '1') : (card.dataset.fltType === vType));
                                const okDate = (vDate === 'ALL') || (card.dataset.fltDate === vDate);
                                const okXing = (vXing === 'ALL') || (card.dataset.fltXing === vXing);
                                const okSurv = (vSurv === 'ALL') || (card.dataset.fltSurv === vSurv);
                                const vis = okType && okDate && okXing && okSurv;
                                card.style.display = vis ? '' : 'none';
                                if (vis) shown += 1;
                            });

                            const isFiltered = (vType !== 'ALL' || vDate !== 'ALL' || vXing !== 'ALL' || vSurv !== 'ALL');
                            const resetBtn = document.getElementById('btnResetLogFilter');
                            if (resetBtn) resetBtn.style.display = isFiltered ? 'inline-block' : 'none';

                            const statusRow = document.getElementById('mtiLogFilterStatusRow');
                            const summaryLbl = document.getElementById('lblLogFilterSummary');
                            if (statusRow && summaryLbl) {
                                statusRow.style.display = isFiltered ? 'flex' : 'none';
                                summaryLbl.textContent = `Showing ${shown} of ${cards.length} Events`;
                            }

                            const emptyMsg = document.getElementById('mtiLogEmptyFilterMsg');
                            if (emptyMsg) emptyMsg.style.display = (cards.length > 0 && shown === 0) ? 'block' : 'none';
                        };

                        window.resetMtiEventLogFilters = function() {
                            ['fltLogType', 'fltLogDate', 'fltLogXing', 'fltLogSurv'].forEach(id => {
                                const el = document.getElementById(id);
                                if (el) el.value = 'ALL';
                            });
                            window.applyMtiEventLogFilters();
                        };

                        if (document.readyState === 'loading') {
                            document.addEventListener('DOMContentLoaded', window.initMtiEventLogFilters);
                        } else {
                            window.initMtiEventLogFilters();
                        }
                    })();
                    </script>
                    <!-- MTI_EVENT_LOG_FILTER_END -->"""

for dash_path in dash_candidates:
    dh = open(dash_path, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    if "<!-- MTI_EVENT_LOG_FILTER_START -->" in dh:
        dh_new, n_rep = re.subn(
            r"[ \t]*<!-- MTI_EVENT_LOG_FILTER_START -->.*?<!-- MTI_EVENT_LOG_FILTER_END -->",
            lambda _m: filter_ui_and_js,
            dh, count=1, flags=re.S
        )
    else:
        dh_new, n_rep = re.subn(
            r"([ \t]*<!-- CHRONOLOGICAL STREAM OF LOGGED INPUT EVENTS -->)",
            lambda m: filter_ui_and_js + "\n\n" + m.group(1),
            dh, count=1
        )
        if not n_rep:
            dh_new, n_rep = re.subn(
                r'([ \t]*<div[^>]*style="max-height:\s*520px;\s*overflow-y:\s*auto;"[^>]*>)',
                lambda m: filter_ui_and_js + "\n" + m.group(1),
                dh, count=1
            )
    if not n_rep:
        raise SystemExit(f"Could not locate Onboard Survey Input Log stream container in {dash_path}!")

    open(dash_path, "w", encoding="utf-8").write(dh_new)
    print(f"  -> Updated {dash_path} (Added Event Type, Date, Crossing & Surveyor dropdown filter bar)")

sync_py = ".venv/Scripts/python.exe" if os.path.exists(".venv/Scripts/python.exe") else "python"
if os.path.exists("sync.py"):
    subprocess.run([sync_py, "sync.py", "feat(mti-ui): add dropdown filter bar for Onboard Survey Input Log"], check=False)
print("\nONBOARD SURVEY INPUT LOG DROPDOWN FILTER COMPLETE & SYNCED!")