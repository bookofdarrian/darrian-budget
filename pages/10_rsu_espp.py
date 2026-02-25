import os
import streamlit as st
import pandas as pd
import anthropic
from datetime import datetime, date
from utils.db import get_conn, init_db, load_investment_context, get_setting
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="RSU/ESPP Advisor — Peach State Savings", page_icon="📈", layout="wide", initial_sidebar_state="auto")
init_db()
require_login()
require_pro("RSU/ESPP Decision Support")
inject_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview", import os
import streamlit as st
import pandas as pd
import anthropic
from datetimensimport s  import pandas as pd
iidimport anthropic
fgefrom datetime",  from utils.db import get_conn, iniicfrom utils.auth import require_login, require_pro, render_sidebar_brand, res 
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(pa"?  )
    load_dotenv()
except ImportErk_except ImportErrab    pass

st.set_p  
st.setn="init_db()
require_login()
require_pro("RSU/ESPP Decision Support")
inject_css()

# ── Sidebar ────────────?trequire_  require_pro("Rghinject_css()

# ── Sidebar ──?e
# ── Ss/8render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview", import os
import streamlit as st
import pandas as pd
import anthropic
from datetimensimport s  impoP st.sidebar.markdown("?t.sidebar.page_link("app("import streamlit as st
import pandas as pd
import anthropic
fromn="🗂️")
st.sidebar.page_link("paimport anthropic
f.pfrom datetimensrkiidimport anthropic
fgefrom datetime",  froagf_link("pages/13_bactry:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(pa"?  )
    load_dotenvBot ?   load_dotenv()
except ImportErliexcept ImportErrin    pass

st.set_pl=
st.setgra    load_", icon="⭐")
rendeexcept ImportErkid
st.set_p  
st.setn="init_db()
require_log─st.setn="?equire_login()
r??require_pro("R?──────────────
# ── S??# ── Sidebar ──?e
# ── Ss/8render_sidebar_brand()
st.sidebar.markdown("---")
s.en# ── Ss/8render_sidebaEYst.sidebar.markdown("---")
st.sideiost.sidebar.page_link("app
 import streamlit as st
import pandas as pd
import anthropic
from datetimensit_import pandas as pd
ii_import anthr      iffrom datet       import pandas as pd
import anthropic
fromn="🗂️")
st.sidebar.page_link("paimport anthropic
f.pfrom??import anthropic
fiofromn="🗂️"cast.sid"Model sellf.pfrom datetimensrkiidimport anthropicaxfgefrom datetime",  froagf_link("pageson risk analysis.")

if not api_key:
    st.warning(    load_dotenv()
except ImportErd.except ImportErrgh    pass

st.set_pke
st.set re    load_dotenvBot ?   l
#except ImportErliexcept ImportErrin   ?st.set_pl=
st.setgra    load_", icon="⭐??t.setgra??endeexcept ImportErkid
st.set_??t.set_p  
st.setn="in??t.setn="??require_log─st.????require_pro("R?───────? ── S??# ── Sidebar ──?e
# ── Ss/8rend??# ── Ss/8render_sidebar_brand()
st.s??st.sidebar.markdown("---")
s.en# ─s.en# ── Ss/8render_s??st.sideiost.sidebar.page_link("app
 import streamlit as sb1 import streamlit as st
import pa Vimport pandas as pd
imSPimport anthropic
f??from datetimensviii_import anthr      iffrom datet   ??mport anthropic
fromn="🗂️")
st.sidebar.page_link("pa?══════st.sidebar.page?.pfrom??import anthropic
fiofromn="🗐═════════
if not api_key:
    st.warning(    load_dotenv()
except ImportErd.except ImportErrgh    pass

st.set_pke
st.set re    load_dotenvBot ??   st.warning??except ImportErd.except ImportE??
st.set_pke
st.set re    load_dotenvBot ???st.set re?except ImportErliexcept ImportErri??st.setgra    load_", icon="⭐??t.setgra??endeex  st.set_??t.set_p  
st.setn="in??t.setn="??require_log─st.???? tst.setn=" and net pr# ── Ss/8rend??# ── Ss/8render_sidebar_brand()
st.s??st.sidebar.markdown("---")
s.en# ─s.en# ── S("#### Grant Dest.s??st.sidebar.markdown("---")
s.en# ─s.en# ─? s.en# ─s.en# ── Ss/8rende_t import streamlit as sb1 import streamlit as st
import pa Vimport panreimport pa Vimport pandas as pd
imSPimport anthy="rsu_shares")
        fmv_at_vef??from datetimensvpufromn="🗂️")
st.sidebar.page_link("pa?══════st.sidebar.pat=st.si", key="rsu_fiofromn="🗐═════════
if not api_key:
    st.warning(    load_doveif not api_key:
    st.warning(    load_      st.warning  except ImportErd.except ImportEva
st.set_pke
st.set re    load_dotenvBot ?? wst.set re
 st.set_pke
st.set re    load_dotenvBot ???st.set re?except ImportErliexcept("st.set rencst.setn="in??t.setn="??require_log─st.???? tst.setn=" and net pr# ── Ss/8rend??# ── Ss/8render_sidebar_brand()
st.s??st.sidebar.markdown("--)
st.s??st.sidebar.markdown("---")
s.en# ─s.en# ── S("#### Grant Dest.s??st.u_state_rate")
        fica_rate     = st.ns.en# ─s.en# ── S("#### G",s.en# ─s.en# ─? s.en# ─s.en# ── Ss/8rende_t import stream,
import pa Vimport panreimport pa Vimport pandas as pd
imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimport anthy="rsu_shares")
        fmv_at_vef??f S       ice ($/share)", min_valust.sidebar.page_link("pa?══════st.sidebarkeif not api_key:
    st.warning(    load_doveif not api_key:
    st.warning(    load_      st.warning  except Importri    st.warningrk    st.warning(    load_      st.warning  o st.set_pke
st.set re    load_dotenvBot ?? wst.set re
 st.set_pke
st.set rlist.set remb st.set_pke
st.set re    load_dotenvBot ?vst.set re vast.s??st.sidebar.markdown("--)
st.s??st.sidebar.markdown("---")
s.en# ─s.en# ── S("#### Grant Dest.s??st.u_state_rate")
        fica_rate     = st.ns.en# ─s.en# ── S("#### G",s.en# ─s.en# s st.s??st.sidebar.markdown("--oms.en# ─s.en# ── S("#### G v        fica_1, key="rsu_existing_shares")
    with c3:
      import pa Vimport panreimport pa Vimport pandas as pd
imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimport anthy="rsu_shareeximSPimport anthy="rsu_shares")
        fmv_at_vreimS??        fmv_at_vreimSPimport ??       fmv_at_vef??f S       ice ($/share)", m?   st.warning(    load_doveif not api_key:
    st.warning(    load_      st.warning  except Importri    st.warningrk    st f    st.warning(    load_      st.warning  l_st.set re    load_dotenvBot ?? wst.set re
 st.set_pke
st.set rlist.set remb st.set_pke
st.set re    load_dotenvBot ?vst.set e  st.set_pke
st.set rlist.set remb st.set_loss from vestst.set re    load_dotenvBot ?ve st.s??st.sidebar.markdown("---")
s.en# ─s.en# ── S("#### Grant Desues.en# ─s.en# ── S("#### G 1        fica_rate     = st.ns.en# ─s.en# ── S("#### G"      with c3:
      import pa Vimport panreimport pa Vimport pandas as pd
imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimport anthy="rsu_shareeximSPimport anthy="rsu_shares")
 or      impormeimSPimport anthy="rsu_shares")
        fmv_at_vreimSPimporco        fmv_at_vreimSPimport y_        fmv_at_vreimS?? * current_price)
    concentration_pct = (new_company_    st.warning(    load_      st.warning  except Importri    st.warningrk    st f    st.warning(    load_      st.warning  l_st.set re    load_do4  st.set_pke
st.set rlist.set remb st.set_pke
st.set re    load_dotenvBot ?vst.set e  st.set_pke
st.set rlist.set remb st.set_loss from vestst.set re    load_dotenvBoaxst.set rli.1st.set re    load_dotenvBot ?vr=st.set rlist.set remb st.set_loss from vestst.set , s.en# ─s.en# ── S("#### Grant Desues.en# ─s.en# ── ntration", f"{concentration_pct:.1f}%",
            import pa Vimport panreimport pa Vimport pandas as pd
imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimport anthy="rsu else "normal")

  imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      impormeimSPimport anthy="rsu_shares")
        fmv_at_vreimSPimporco [        fmv_at_vreimSPimporco        fmv_at_v,     concentration_pct = (new_company_    st.warning(    load_      st.warning  except Importri    s}"st.set rlist.set remb st.set_pke
st.set re    load_dotenvBot ?vst.set e  st.set_pke
st.set rlist.set remb st.set_loss from vestst.set re    load_dotenvBoaxst.set rli.1st.set re    load_dotenvBo  st.set re    load_dotenvBot ?v  st.set rlist.set remb st.set_loss from vestst.set ra            import pa Vimport panreimport pa Vimport pandas as pd
imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimport anthy="rsu else "normal")

  imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimport anthom        fmv_at_vreimSPimport f"
  imSPimport anthy="rsu_s "Unrealized Gain/Loss", "LTCG        fmv_at_vreimSPimpor)
  if        fmv_at_vreimSPimpor"A        fmv_at_vreimSPimporco [        fmv_at_vreimSPimporco        fmv_at_vowst.set re    load_dotenvBot ?vst.set e  st.set_pke
st.set rlist.set remb st.set_loss from vestst.set re    load_dotenvBoaxst.set rli.1st.set re    load_dotenvBo  st.set re    load_dotenvBot ?v  st.set rlist.st.st.set rlist.set remb st.set_loss from vestst.sr_widimSPimport anthy="rsu_shares")
        fmv_at_vreimSPimport anthy="rsu else "normal")

  imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
    ??──────?       fmv_at_vreimSPimport ??────────────────
    st.        fmv_at_vreimSPimpor)
  an        fmv_at_vreimSPimporle      imSPimport anthy="rsu_shares")
        fmvAd        fmv_at_vreimSPimport anthomto  imSPimport anthy="rsu_s "Unrealized Gain/Loss", "LTCG   "rsu_sche  if        fmv_at_vreimSPimpor"A        fmv_at_vreimSPimporco [        fmv_at_vre  st.set rlist.set remb st.set_loss from vestst.set re    load_dotenvBoaxst.set rli.1st.set re    load_dotenvBo  st.set re    load_dotenvBot ?v  st.set rlist.st.sha        fmv_at_vreimSPimport anthy="rsu else "normal")

  imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", value="AAPL", key="sv_tick
  imSPimport anthy="rsu_shares")
        fmv_at_vrei"ad        fmv_at_vreimSPimpor)
  n_        fmv_at_vreimSPimpord(      imSPimport anthy="rsu_shares")
    ??─?     ??──────?         "S    st.        fmv_at_vreimSPimpor)
  an        fmv_at_vreimSPimporle      imSPimport anthy="rsu_shares".)  an        fmv_at_vreimSPimporle ra        fmvAd        fmv_at_vreimSPimport anthomto  imSPimport anthy,

  imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", value="AAPL", key="sv_tick
  imSPimport anthy="rsu_shares")
        fmv_at_vrei"ad        fmv_at_vreimSPimpor)
  n_        fmv_at_vreimSPimpord(      imSPimport anthy="rsu_shares")
    ??─?     ??──────?         "S    st.        fmv_at_vr([s         pd.DataFrame([totals])],        fmv_at_vreimSPimpor        imSPimport anthy="rsu_shares")
  "Ticker",e.  "Ticker", value="AAPL", key="sv_tes  imSP"${:,.2f}", "Net": "${:,.2f}"}),
        fmv_at_vrei"ad        fid  n_        fmv_at_vreimSPimpord(      imSPimport      ??─?     ??─────le", key="clear_sched"):
             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu_shares".)  an        fm??  imSPimport anthy="rsu_shares")
        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", value="AAPL"???       fmv_at_vreimSPimpor)
  ??       fmv_at_vreimSPimporES      imSPimport anthy="rs??═══════? "Ticker", value="AAPL", key="sv_t? imSPimport anthy="rsu_shares")
    ?       fmv_at_vrei"ad        f? n_        fmv_at_vreimSPimpord(      imSPi??═?   ??─?     ??──────?         "S    st.        feade  "Ticker",e.  "Ticker", value="AAPL", key="sv_tes  imSP"${:,.2f}", "Net": "${:,.2f}"}),
        fmv_at_vrei"ad        fid  n_        fmv_at_vreimSPimpord(      imSPimport             fmv_at_vrei"ad        fi### ESPP Plan Details")
        espp_ticker       = st.te             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu_shares".)  an        fm??  imSPimport anthy="rsu_shares")
        fmre        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vreimSPimporin      imSPimport anthy="rsu_shares")
  "Ticker",er  "Ticker", value="AAPL"???       e)  ??       fmv_at_vreimSPimporES      imSPimport anthur    ?       fmv_at_vrei"ad        f? n_        fmv_at_vreimSPimpord(      imSPi??═?   ??─?     ??──────?         "S    st.    SP        fmv_at_vrei"ad        fid  n_        fmv_at_vreimSPimpord(      imSPimport             fmv_at_vrei"ad        fi### ESPP Plan Details")
        espp_ticker       = st.te             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu          espp_ticker       = st.te             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu_shares".)  an        fm??  imSPimpo##        fmre        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri      imSPimport anthy="rsu_shares")($/share)", mi  "Ticker", vic        fmv_at_vreimri  "Ticker",er  "Ticker", value="AAPL"???       e)  ??       fmv_at_vreimSPimp
         espp_ticker       = st.te             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu          espp_ticker       = st.te             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu_shares".)  an        fm??  imSPimpo##        fmre        fmv_at_vreimSPimpor)
        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", vic        ?       fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri      imSPimport anthy="rsu_shares")($/share)", mi  "Ticker", vic        fmv_at_vreimri  "Ticker",er  "Ticker", value="AAPL"spp_shares * espp_actual_cost
    espp_discount_gain  "Ticker", vic        fmv_at_vrei st         espp_ticker       = st.te             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu          espp_ticker       = st.te             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu_shares".)  an        fm??  im_f        fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", vic        ?       fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri      imSPimp_p      imSPimport anthy="rsu_shares")
  "Ticker",    "Ticker", vic        ?       fmin      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei kx(  "Ticker", vic        fmv_at_vrei       espp_discount_gain  "Ticker", vic        fmv_at_vrei st         espp_ticker       = st.te             an        fmv_at_vreimSPimporle      imSPimport anthy="rsu          espp_ticker       = st.te             an        fmv_at_Co      imSPimport anthy="rsu_shares")
  "Ticker", vic        ?       fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri      imSPimp_p      imSPimport anthy="rsu_shares")
  "Ticker",    "Ticker", vic        ?       fmin      imSPimport ant.colu  "Ticker", vic        ?       fmst      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei kda  "Ticker", vic        fmv ["Purchase  "Ticker",    "Ticker", vic        ?       fmin      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei kx(  _c  "Ticker", vic        fmv_at_vrei kx(  "Ticker", vic        fmv_at_vrei       espp_dax  "Ticker", vic        ?       fmv_at_vreimSPimport t. or      im Vest")
      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri      imSPimp_p      imSPimport anthy="rsu_shares")
  "Ticker",    "Ticker", vic        ?       fmin      imSPimport ant.colu  "Ticker", vic        ?       imSPimport anthy="rsu_shares")
  "Ticker", vic        fm Income Porti  "Ticker", vic        fmv_at_vrei io  "Ticker",    "Ticker", vic        ?       fmin      imSPimport ant.colu  "Ticker", vic        ?       fmst      imSPimporf}  "Ticker", vic        fmv_at_vrei kda  "Ticker", vic        fmv ["Purchase  "Ticker",    "Ticker", vic        ?       fmin      imSPimport anthy    "Ticker", vic        fmv_at_vrei kx(  _c  "Ticker", vic        fmv_at_vrei kx(  "Ticker", vic        fmv_at_vrei       espp_dax  "Ticker", vic        ?      d      imSPimport anthy="rsu_shares")
  "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri      imSPimp_p      imSPimport anthy="rsu_shares")
  "Ticker",    "Ticker", vic        ? "Ticker", vic        fmv_at_vrei ??  "Ticker",    "Ticker", vic        ?       fmin      imSPimport ant.colu  "Ticker", vic        ?       imSPimport anthy="r?? "Ticker", vic        fm Income Porti  "Ticker", vic        fmv_at_vrei io  "Ticker",    "Ticker", vic        ?       fmin      imSPim? "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri      imSPimp_p      imSPimport anthy="rsu_shares")
  "Ticker",    "Ticker", vic        ? "Ticker", vic        fmv_at_vrei ??  "Ticker",    "Ticker", vic        ?       fmin      imSPimport ant.colu  "Ticker", vic        ?       imSPimport anthy="r?? "Ticker", vic        fm Income Porti  "Ticker", vic        fmv_at_vrei io  "Ticker",    "Ticker", vic        ?       fmin      imSPim? "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri ke  "Ticker",    "Ticker", vic        ? "Ticker", vic        fmv_at_vrei ??  "Ticker",    "Ticker", vic        ?       fmin  rr  "Ticker",    "Ticker", vic        ? "Ticker", vic        fmv_at_vrei ??  "Ticker",    "Ticker", vic        ?       fmin      imSPimport ant.colu  "Ticker", vic        ?       imSPimport anthy="r?? "Ticker", vic        fm Income Porti  "Ticker", vic        fmv_at_vrei io  "Ticker",    "Ticker", vic        ?       fmin      imSPim? "Ticker", vic        fmv_at_vrei k        fmv_at_vreimSPimport t. or     ri ke  "Ticker",    "Ticker", vic        ? "Tickerl Context", placeholder="e.g. 'I have 4 more vest events this year', 'Company has earnings next week', 'I need cash for a house down payment'", key="ai_notes", height=80)

    if st.button("🤖 Get AI Recommendation", type="primary", key="btn_ai_rsu"):
        gross = ai_shares_vest * ai_fmv
        tax_rate = (ai_fed_rate + ai_state_rate + 7.65) / 100
        net_sell = gross * (1 - tax_rate)
        hold_val = ai_shares_vest * ai_current_px

        context = f"""
RSU/ESPP Decision Analysis Request:
- Company: {ai_ticker_sym}
- Shares vesting: {ai_shares_vest}
- FMV at vest: ${ai_fmv:.2f}/share
- Current price: ${ai_current_px:.2f}/share
- Gross RSU income: ${gross:,.2f}
- Estimated tax rate (fed + state + FICA): {tax_rate*100:.1f}%
- Net proceeds if sold at vest: ${net_sell:,.2f}
- Current hold value: ${hold_val:,.2f}
- Total portfolio value: ${ai_portfolio_val:,.2f}
- Current concentration in this stock: {ai_company_pct}%
- After vesting, new concentration would be: {((ai_company_pct/100*ai_portfolio_val +
    if st.button("🤖 Get AI Recommendation", type="primary", key="btn_ai_rsu"):
        gross = ai_shares_vest * ai_fmv
        tax_rate = (ai_fed_rate + ai_state_r0):        gross = ai_shares_vest * ai_fmv
        tax_rate = (ai_fed_rate + ai_staot  }
"""
        prompt = """Analyze this        net_sell = gross * (1 - tax_rate)
        hold_val =nd        hold_val = ai_shares_vest * ai_cse
        contexold)
2. Concentration risk assessment (is this too much sin- Company: {ai_ticker_sym}
- Sharefi- Shares vesting: {ai_shaso- FMV at vest: ${ai_fmv:.2f}/sharon- Current price: ${ai_currenttion p- Gross RSU income: ${gross:,.2f}
- Estimabe- Estimated tax rate (fed + statol- Net proceeds if sold at vest: ${net_sell:,.2f}
- Current hoh st.spinner("Claude is analyzing your RSU situatio- Total portfolio value: ${ai_portfol  - Current concentration in this stock: {ai_compa  - After vesting, new concentrasages.create(
                 if st.button("🤖 Get AI Recommendation", type="primary", key="btn_ai_rsu"):
            gross = ai_shares_vest * ai_fmv
        tax_rate = (ai_fed_rate + ai_sta s        tax_rate = (ai_fed_rate + ai_sn{        tax_rate = (ai_fed_rate + ai_staot  }
"""
        prompt = """Analyze thisent[0"""
        prompt = """Analyze this        t.  rk        hold_val =nd  ommendation")
                st.text(response_text)        contexold)
2. Concentration risk assessment (is this ag2. Concentration 1_- Sharefi- Shares vesting: {ai_shaso- FMV at vest: ${ai_fmv:.2f}/sharon- Currenst- Estimabe- Estimated tax rate (fed + statol- Net proceeds if sold at vest: ${net_sell:,.2f}
- Current hoh st.spinner("Claude is analyzingic- Current hoh st.spinner("Claude is analyzing your RSU situatio- Total portfolio value: ${af"                 if st.button("🤖 Get AI Recommendation", type="primary", key="btn_ai_rsu"):
            gross = ai_shares_vest * ai_fmv
        tax_rate = (ai_fed_rate + ai_sta s        tax_r"?           gross = ai_shares_vest * ai_fmv
        tax_rate = (ai_fed_rate + ai_sta s      adv        tax_rate = (ai_fituation.")
