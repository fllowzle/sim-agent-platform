import sys; sys.path.insert(0,'src')
from sim_agent.adapters.mcp_wizard import McpWizard, create_profile_quick
w = McpWizard()
answers = {'software_name':'ANSYS','python_sdk':'pyansys','sdk_install':'pip install pyansys','connection_mode':'1','domain_count':'s,t','error_count':'e1,e2','template_count':'t1,t2','keywords_per_domain':'k1,k2','core_tools':'c1,c2'}
c = 0
while True:
    q = w.get_next_question()
    if q is None: break
    c += 1
    w.answer(q['step_id'], q['question']['id'], answers.get(q['question']['id'], 'test'))
    print(f'  Q{c}: {q["question"]["id"]} answered')
assert w.profile.config_complete
assert w.profile.name == 'ANSYS'
plan = w.generate_file_plan()
assert 'files_to_create' in plan
qp = create_profile_quick('QS','qsd','pip','cli')
assert qp.name == 'QS'
print(f'WIZARD: {c} questions, profile OK, plan OK, quick profile OK')
print('ALL WIZARD TESTS PASSED')