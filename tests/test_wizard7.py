import sys; sys.path.insert(0,'src')
from sim_agent.adapters.mcp_wizard import McpWizard
w = McpWizard()
answers = {'software_name':'T','python_sdk':'t','sdk_install':'t','connection_mode':'1','domain_count':'a','error_count':'a','template_count':'a','keywords_per_domain':'a','core_tools':'a','guides_dir':'skip','pdf_dir':'skip','pdf_relevance':'a:b'}
c = 0
while True:
    q = w.get_next_question()
    if q is None: break
    c += 1
    w.answer(q['step_id'], q['question']['id'], answers.get(q['question']['id'], 'x'))
    print('Step', q.get('step','?'), ':', q['question']['id'], '=', answers.get(q['question']['id'], 'x')[:15])
print('Total questions:', c)
print('Config complete:', w.profile.config_complete)
print('Has KB config:', hasattr(w.profile, '_kb_guides_dir'))