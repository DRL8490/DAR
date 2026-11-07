import os
import ast
import subprocess

# Clean up leftover check_stage.py if present
if os.path.exists("check_stage.py"):
    os.remove("check_stage.py")

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

old_del_block = '''                                <td class="text-end">
                                    <form action="/mti/delete_fix/{{ r.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete Unit #{{ r.unit_no }} from ledger?');">
                                        <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-1"><i class="fas fa-trash"></i></button>
                                    </form>
                                </td>'''

new_del_block = '''                                <td class="text-end text-nowrap">
                                    <button type="button" class="btn btn-sm btn-outline-primary py-0 px-1 me-1" title="Edit Unit #{{ r.unit_no }}"
                                            data-unit="{{ r.unit_no }}"
                                            data-first="{{ 'true' if (r.is_first_in_array or r.unit_no == 1) else 'false' }}"
                                            data-crossing="{{ r.crossing_id }}"
                                            data-box="{{ r.design_box_id }}"
                                            data-tag="{{ r.physical_tag }}"
                                            data-date="{{ r.install_date }}"
                                            data-des-e="{{ '%.3f'|format(r.design_e|float) }}"
                                            data-des-n="{{ '%.3f'|format(r.design_n|float) }}"
                                            data-as-e="{{ '%.3f'|format(r.aslaid_e|float) }}"
                                            data-as-n="{{ '%.3f'|format(r.aslaid_n|float) }}"
                                            data-cl="{{ '%.2f'|format(r.cl_offset_m|float) }}"
                                            data-hdg="{{ '%.3f'|format(r.heading_deg|float) }}"
                                            data-gap1="{{ '%.2f'|format(r.gap1_m|default(r.gap_m)|float) }}"
                                            data-gap2="{{ '%.2f'|format(r.gap2_m|default(r.gap_m)|float) }}"
                                            data-status="{{ r.status }}"
                                            data-remarks="{{ r.remarks }}"
                                            onclick="editFixRow(this)">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <form action="/mti/delete_fix/{{ r.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete Unit #{{ r.unit_no }} from ledger?');">
                                        <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-1" title="Delete Unit #{{ r.unit_no }}"><i class="fas fa-trash"></i></button>
                                    </form>
                                </td>'''

old_tl_footer = '''                            <div class="small text-muted border-top pt-1">{{ tl.notes }}</div>
                        </div>'''

new_tl_footer = '''                            <div class="d-flex justify-content-between align-items-center border-top pt-2 mt-1 gap-2">
                                <div class="small text-muted">{{ tl.notes }}</div>
                                <div class="text-nowrap">
                                    <button type="button" class="btn btn-sm btn-outline-primary py-0 px-1 me-1" title="Edit {{ tl.log_date }} Shift Log"
                                            data-date="{{ tl.log_date }}"
                                            data-surv="{{ tl.surveyors }}"
                                            data-pos="{{ tl.hrs_positioning }}"
                                            data-trb="{{ tl.hrs_survey_troubleshooting }}"
                                            data-rov="{{ tl.hrs_rov_recovery }}"
                                            data-dp="{{ tl.hrs_deck_dp }}"
                                            data-stb="{{ tl.hrs_standby }}"
                                            data-notes="{{ tl.notes }}"
                                            onclick="editTimeLogRow(this)">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <form action="/mti/delete_timelog/{{ tl.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete 24h Shift Log for {{ tl.log_date }}?');">
                                        <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-1" title="Delete Shift Log"><i class="fas fa-trash"></i></button>
                                    </form>
                                </div>
                            </div>
                        </div>'''

js_edit_helpers = '''    function editFixRow(btn) {
        const d = btn.dataset;
        const drawerEl = document.getElementById('addFixDrawer');
        if (drawerEl && !drawerEl.classList.contains('show')) {
            new bootstrap.Collapse(drawerEl, { toggle: true });
        }
        const f = drawerEl.querySelector('form');
        f.querySelector('[name="unit_no"]').value = d.unit;
        const chkFirst = document.getElementById('chkFirstMattress');
        if (chkFirst) chkFirst.checked = (d.first === 'true');
        f.querySelector('[name="crossing_id"]').value = d.crossing;
        f.querySelector('[name="design_box_id"]').value = d.box;
        f.querySelector('[name="physical_tag"]').value = d.tag;
        f.querySelector('[name="install_date"]').value = d.date;
        document.getElementById('inpDesE').value = d.desE;
        document.getElementById('inpDesN').value = d.desN;
        document.getElementById('inpAsE').value = d.asE;
        document.getElementById('inpAsN').value = d.asN;
        document.getElementById('inpClOff').value = d.cl;
        f.querySelector('[name="heading_deg"]').value = d.hdg;
        if (document.getElementById('inpGap1')) document.getElementById('inpGap1').value = d.gap1;
        if (document.getElementById('inpGap2')) document.getElementById('inpGap2').value = d.gap2;
        f.querySelector('[name="status"]').value = d.status;
        f.querySelector('[name="remarks"]').value = d.remarks;
        if (typeof toggleGapInputs === 'function') toggleGapInputs();
        drawerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function editTimeLogRow(btn) {
        const d = btn.dataset;
        const drawerEl = document.getElementById('addTimeLogDrawer');
        if (drawerEl && !drawerEl.classList.contains('show')) {
            new bootstrap.Collapse(drawerEl, { toggle: true });
        }
        const f = drawerEl.querySelector('form');
        f.querySelector('[name="log_date"]').value = d.date;
        f.querySelector('[name="surveyors"]').value = d.surv;
        f.querySelector('[name="hrs_positioning"]').value = d.pos;
        f.querySelector('[name="hrs_survey_troubleshooting"]').value = d.trb;
        f.querySelector('[name="hrs_rov_recovery"]').value = d.rov;
        f.querySelector('[name="hrs_deck_dp"]').value = d.dp;
        f.querySelector('[name="hrs_standby"]').value = d.stb;
        f.querySelector('[name="notes"]').value = d.notes;
        drawerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function calcOffset() {'''

del_tlog_route = '''
@mti_bp.route('/delete_timelog/<int:tlog_id>', methods=['POST'])
@login_required
def delete_timelog(tlog_id):
    state = load_mti_state()
    state["time_logs"] = [t for t in state.get("time_logs", []) if int(t.get("id", 0)) != tlog_id]
    save_mti_state(state)
    flash("Removed 24-Hour Shift Time Audit entry.", "success")
    return redirect(url_for('mti_bp.mti_dashboard'))
'''

if "editFixRow" not in mc:
    mc = mc.replace(old_del_block, new_del_block, 1)
    mc = mc.replace(old_tl_footer, new_tl_footer, 1)
    mc = mc.replace("    function calcOffset() {", js_edit_helpers, 1)
    mc += "\n" + del_tlog_route

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)

print("1. Added 1-click Edit buttons to MTI Fix Ledger and 24-Hour Shift Logs.")
subprocess.run(["py", "sync.py", "feat: add 1-click inline edit to MTI ledger rows and 24h shift logs"], check=False)
