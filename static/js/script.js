//index

function doubleConfirm() {
    if (!confirm("정말 전체 데이터를 초기화하시겠습니까?")) return false;
    if (!confirm("이 작업은 되돌릴 수 없습니다. 계속 진행할까요?")) return false;
    location.href = "/inc/rent_createtb.php";
    return false;
}


// ------------------ 로그인 / 로그아웃 ------------------
function login() {
    var f = document.getElementById("frm_login");
    if (f.u_id.value.trim() === "") { alert("ID를 입력하세요."); f.u_id.focus(); return false; }
    if (f.u_pw.value.trim() === "") { alert("PW를 입력하세요."); f.u_pw.focus(); return; }
// alert("PW를 입력하세요."+f.u_id.value+f.u_pw.value);
    f.action="../inc/rent_write.php?f_type=check_id";
	//alert("PW를 입력하세요."+f.u_id.value+f.u_pw.value);
    f.submit();
}

function user_logout() {
    if (confirm("로그아웃을 할까요?")) {
        const f = document.getElementById("frm_login");
        f.action="../inc/rent_write.php?f_type=log_out";
        f.submit();             
    }
}

function user_add(){
    var f=document.getElementById("frm_add");
    var uid=f.querySelector("input[name='u_id']");
    var upw=f.querySelector("input[name='u_pw']");
    var manage=f.querySelector("input[name='h_manage']");

    if(uid.value.trim()===""){alert("추가할 ID를 입력하세요.");uid.focus();return;}
    if(upw.value.trim()===""){alert("PW를 입력하세요.");upw.focus();return;}
    if(manage.value.trim()===""){
        document.getElementsByName("btn_login")[0].disabled=true;
        alert("관리할 주택이름을 A,B,C 이렇게 입력하세요.");
        manage.focus();
        return;
    }

    f.action="/rent_write?f_type=user_add";
    f.submit();
}
// ------------------ 사용자 관리 fetch ------------------
var manageLoaded = false; // 한 번만 로드


// ------------------ ID 중복 체크 ------------------
function user_id_check() {
    var inputEl = document.getElementById("u_id");
    if (!inputEl) {
        alert("u_id 입력란이 없습니다.");
        return;
    }

    var uid = inputEl.value.trim();

    if (uid === "") {
        alert("추가할 ID를 입력하세요.");
        inputEl.focus();
        return;
    }

    var xhr = new XMLHttpRequest();

    xhr.open(
        "GET",
        "/check?type=id&u_id=" + encodeURIComponent(uid),
        true
    );

    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4 && xhr.status === 200) {

            var resp = xhr.responseText.trim();

            if (resp === "exist") {

                alert("이미 사용 중인 아이디입니다.");

                document.getElementsByName("btn_login")[0].disabled = true;

                var inputEl = document.getElementById("u_id");
                inputEl.value = "";
                inputEl.focus();

            } else if (resp === "ok") {

                alert("사용 가능한 아이디입니다.");

                document.getElementsByName("btn_login")[0].disabled = false;
                document.getElementsByName("btn_id_check")[0].disabled = true;
            }
        }
    };

    xhr.send();
}

// ------------------ 주택명 중복 체크 ------------------
function house_name_check() {

    var inputEl = document.getElementById("h_manage");

    var housename = inputEl.value.trim();

    if (housename === "") {
        alert("주택명을 입력하세요.");
        inputEl.focus();
        return;
    }

    var xhr = new XMLHttpRequest();
    
    xhr.open(
        "GET",
        "/check?type=house&house_name=" + encodeURIComponent(housename),
        true
    );

    xhr.onreadystatechange = function() {

        if (xhr.readyState !== 4) {
            return;
        }

        if (xhr.status !== 200) {
            alert("주택명 중복 확인에 실패했습니다. HTTP " + xhr.status);
            return;
        }

        var resp = xhr.responseText.trim();

        if (resp === "exist") {

            alert("이미 등록된 주택이름이 있습니다.");
            document.getElementsByName("btn_login")[0].disabled = true;
            inputEl.value = "";
            inputEl.focus();

        } else if (resp === "ok") {

            alert("사용 가능한 주택 이름입니다.");
			document.getElementsByName("btn_login")[0].disabled = false;

        } else {

            alert("중복 확인 결과 오류: [" + resp + "]");
        }
    };

    xhr.send();
}

async function runCheck(form) {
    if (!form) return false;

    var inputEl = form.querySelector('input[name="h_manage"]');
    var submitBtn = form.querySelector('button[type="submit"]');
   // alert("주택명을 입력해주세요." +inputEl +"submitBtn="+submitBtn +"form.name="+form.name);
    if (!inputEl) return false;

    // 🌟 핵심: 현재 폼이 속한 <tr>(행)을 찾고, 첫 번째 <td>의 u_id 텍스트 추출
    var trEl = form.closest('tr');
    var targetUid = "";
    if (trEl) {
        var firstTd = trEl.querySelector('td');
        if (firstTd) {
            targetUid = firstTd.textContent.trim(); // "admin" 등 u_id 추출
        }
    }

    inputEl.value = inputEl.value.trim();
    var housename = inputEl.value;

    if (!housename) {
        alert("주택명을 입력해주세요.");
        inputEl.focus();
        return false;
    }

    // 🌟 target_uid 파라미터로 추출한 u_id 전송
    var url = "/check?type=house&house_name=" + encodeURIComponent(housename) 
            + "&target_uid=" + encodeURIComponent(targetUid);

    try {
        var response = await fetch(url);
        if (!response.ok) {
            throw new Error("HTTP error " + response.status);
        }
        
        var text = await response.text();
        var resp = text.trim();

        if (resp === "exist" || resp === "exists") {
            alert("이미 다른 사용자에게 등록된 주택이름이 있습니다.");
            inputEl.focus();
            if (submitBtn) submitBtn.disabled = true;
            return false; // 중복 시 제출 막음
        } else if (resp === "ok") {
            if (submitBtn) submitBtn.disabled = false;
            return true;  // 사용 가능 시 submit 실행
        } else {
            alert("중복 확인 결과 오류: [" + resp + "]");
            if (submitBtn) submitBtn.disabled = true;
            return false;
        }
    } catch (error) {
        alert("중복 확인 중 오류가 발생했습니다: " + error.message);
        if (submitBtn) submitBtn.disabled = true;
        return false;
    }
}


//등록된 관리주택을 수정할때 중복방지 체크하기 위한 함수-------------------------------------
function checkAndSubmitHouse(btnEl) {
    // 버튼이 포함된 상위 form 요소 찾기
    var form = btnEl.closest("form");
    if (!form) return;

    // 해당 form 내부의 h_manage 입력 필드 찾기
    var inputEl = form.querySelector('input[name="h_manage"]');
    if (!inputEl) return;

    var housename = inputEl.value.trim();

    if (!housename) {
        alert("주택명을 입력해주세요.");
        inputEl.focus();
        return;
    }

    // GET 방식으로 Flask 중복 체크 라우트에 요청
    var url = "/check?type=house&house_name=" + encodeURIComponent(housename);

    fetch(url)
        .then(function(response) {
            if (!response.ok) {
                throw new Error("HTTP error " + response.status);
            }
            return response.text();
        })
        .then(function(text) {
            var resp = text.trim();

            if (resp === "exist" || resp === "exists") {
                alert("이미 등록된 주택이름이 있습니다.");
                inputEl.value = "";
                inputEl.focus();
            } else if (resp === "ok") {
               
                form.submit();
            } else {
                alert("중복 확인 결과 오류: [" + resp + "]");
            }
        })
        .catch(function(error) {
            alert("중복 확인 중 오류가 발생했습니다: " + error.message);
        });
}

//---------------하우스정보 등록 스크립트 모음==============================
function frmsubmit_house(vv){
    var frmsub = document.frm_house_info;
    var obj;

    obj = frmsub.opt_house;
    if (obj.value == "") {
        alert("주택이름을 입력하세요");
        obj.focus();
        return;
    }

    obj = frmsub.m_address;
    if (obj.value == "") {
        alert("주택 소재지주소를 입력하세요");
        obj.focus();
        return;
    }

    obj = frmsub.m_room_all;
    if (obj.value == "") {
        alert("주택 구별 101,102,103,,,로 입력하세요");
        obj.focus();
        return;
    }

    obj = frmsub.m_name;
    if (obj.value == "") {
        alert("관리자 이름을 입력하세요");
        obj.focus();
        return;
    }

    obj = frmsub.m_phone;
    if (obj.value == "") {
        alert("관리자 전화번호를 입력하세요");
        obj.focus();
        return;
    }

    if(vv == "add") {   
        alert("제출합니다.");
        frmsub.action = "/rent_write?p=1&f_type=house_add";
        frmsub.submit();
    } 
    if(vv == "edit") {
        frmsub.action = "/rent_write?p=1&f_type=house_edit";
        if (!confirm(frmsub.action + "을(를) 정말 수정할까요?")) { return; }
        frmsub.opt_house.disabled = false;
        frmsub.btn_edit.style.backgroundColor = "#D5D5D5";
        frmsub.submit();
    }
}

function house_info_load(id, h_house, ad, arralll, name, phone) {
    var f = document.querySelector("form[name='frm_house_info']");
    var sel = f.opt_house;
    var val = h_house;
    if (!sel.querySelector(`option[value="${val}"]`)) { 
        sel.add(new Option(val, val));
    }
    sel.value = val;

    f.m_address.value = ad;
    f.m_room_all.value = arralll;
    f.m_name.value = name;
    f.m_phone.value = phone;
    f.btn_renter_add.disabled = true; 
    
    f.btn_edit.style.backgroundColor = "#FFBB00";
    f.btn_edit.value = h_house + " 수정";
    f.btn_edit.disabled = false;
    f.opt_house.disabled = false;
}


//--------------------------------------------------------
//pay_state
//========================================================

function add_cencel(){
var f=document.ipkum_add_form;
   f.reset();

    f.water_ck.value=false;
   f.btn_ip_kum_add.style.backgroundColor = "#E7E7E7";
   f.btn_ip_kum_add.value="등록";
}

function load_ipkum_data_edit(id_num, ipkum_day, house_name, room_num, renter_name, ipkum_won, water){
    var f = document.ipkum_add_form;
    
    // 동작 확인용 (콘솔을 추천하지만 alert도 무방합니다)
    console.log("수정 모드 진입: " + house_name); 

    f.id_num.value = id_num;
    f.room_num.value = room_num;
    f.house_name.value = house_name;
    f.ipkum_won.value = ipkum_won;
    f.ipkum_name.value = renter_name;
    f.ipkum_date.value = ipkum_day;

    // 수도세 체크 여부 (1이면 체크, 0이면 해제)
    f.water_ck.checked = (water == 1 || water === "1");

    // 버튼 UI 변경
    f.btn_ip_kum_add.style.backgroundColor = "#FFBB00";
    f.btn_ip_kum_add.value = "수정";
}

function auto_ipkum_add(h_name, r_num, r_name, r_price) {
    if (!h_name) {
        alert("등록할 주택이름이 없습니다.");
        return;
    }

    // Flask 라우트 URL 경로로 수정 (프로젝트 URL 구조에 맞게 변경)
    var aa = "/rent_write?p=4"
        + "&f_type=ipkum_auto_add"
        + "&house_name=" + encodeURIComponent(h_name)
        + "&room_num=" + encodeURIComponent(r_num)
        + "&ipkum_name=" + encodeURIComponent(r_name)
        + "&ipkum_won=" + encodeURIComponent(r_price);

    if (confirm(r_name + " [" + r_price + "] 의 금액을 입금으로 저장할까요?")) {
        location.href = aa;
    }
}

function year_onchange(s_date) {
    var houseEl = document.getElementById("opt_house");
    var roomEl  = document.getElementById("opt_num");

    var house_name = houseEl ? houseEl.value : "";
    var room_num   = roomEl  ? roomEl.value  : "";
    
   
    location.href = "m_pay_state?p=4"
        + "&house_name=" + encodeURIComponent(house_name)
        + "&room_num="   + encodeURIComponent(room_num)
        + "&s_date="     + encodeURIComponent(s_date);
}

function num_pay_onchange(r_house,r_num) {
    
    var houseSelect = document.getElementById("house_name");
    var roomSelect  = document.getElementById("room_num");
    var dateSelect  = document.getElementById("s_date");
 
    // 요소가 있을 경우 해당 값 사용, 없으면 빈 값
    var houseName = houseSelect ? houseSelect.value : "";
    var roomNum   = roomSelect  ? roomSelect.value  : "";
    var sDate     = dateSelect  ? dateSelect.value  : "";

    // 2. 파라미터를 모두 조합하여 URL 재구성
    var url = "/m_pay_state?p=4"
            + "&house_name=" + encodeURIComponent(r_house)
            + "&room_num="   + encodeURIComponent(r_num)
            + "&s_date="     + encodeURIComponent(sDate);

    // 3. 페이지 이동
    location.href = url;
}

function ipkum_add_submit() {
    var frm = document.ipkum_add_form;

    // 필수 입력값 확인 함수

 function checkField(field, message) {
        if (!field.value.trim()) {
            alert(message);
            field.focus();
            return false;
        }
        return true;
    }

    // 필수 필드 검사
	
  //  if (!checkField(frm.id_num, "id_num 가 없어서 수정을 할수 없습니다.")) return;
    if (!checkField(frm.ipkum_won, "입금 금액을 입력하세요")) return;
    if (!checkField(frm.ipkum_name, "입금자 이름을 입력하세요")) return;

    var actionType = frm.btn_ip_kum_add.value;
    var roomInfo = frm.house_name.value + "[" + frm.room_num.value + "]";

    if (actionType === "등록") {
        if (!confirm(roomInfo + " 을(를) 등록 할까요?")) return;
        frm.action = "/rent_write?p=4&f_type=ipkum_add";

    } else if (actionType === "수정") {
        if (!confirm(roomInfo + " 을(를) 수정 할까요?")) return;

        if (frm.house_name.value === "") {
            alert("수정할 주택이름이 없습니다.");
            return;
        }
        if (frm.room_num.value === "") {
            alert("주택의 호수가 없습니다.");
            return;
        }
        frm.btn_ip_kum_add.style.backgroundColor = "#D5D5D5";
        frm.action = "/rent_write?p=4&f_type=ipkum_edit";
    }

    frm.submit();
}

function delete_ipkum(id_num){
	if (!confirm(id_num+"["+ id_num +"] 을(를) 정말삭제  할까요?")){return;}
 		location.href ="/rent_write?p=4&f_type=ipkum_delete&id_num=" + id_num;
}

//-------------------------------------------------------
//함수들
//=======================================================</script>
function fncChk(input_str, type_sw) {
    var fm = input_str;
    switch(type_sw) {
        case 1:
            var ptn = /[^\d]/;
            if(fm.search(ptn) != -1) alert('숫자만 입력 가능합니다.');
            break;
        case 2:
            var ptn = /\d/;
            if(fm.search(ptn) != -1) alert('문자만 입력 가능합니다.');
            break;
    }
}

function house_add_cancel() {
    var f = document.querySelector("form[name='frm_house_info']");
    if (!f) return;

    f.querySelectorAll("input[type=text], input[type=hidden], textarea").forEach(el => {
        if (el.name !== 'opt_house') el.value = "";
    });

    f.querySelectorAll("select").forEach(sel => {
        if (sel.name !== 'opt_house') sel.selectedIndex = 0;
    });
     
    f.btn_renter_del.value = "삭제";
    f.btn_renter_add.disabled = false;
    f.btn_renter_del.disabled = false; 
    f.btn_edit.disabled = true; 
    f.btn_edit.style.backgroundColor = "#E7E7E7";
    f.btn_edit.value = "수정";
    f.opt_house.disabled = false;
}

function house_del(house_name, id) {
    if (!confirm(house_name + "을(를) 정말 삭제할까요?")) { return; }
    document.location.href = "/rent_write?f_type=house_del&id=" + id;
}


function togglePassword() {
    const pwInput = document.getElementById('u_pw');
    const toggleBtn = document.getElementById('toggleBtn');
    if (pwInput.type === 'password') {
        pwInput.type = 'text';
        toggleBtn.textContent = 'H';
    } else {
        pwInput.type = 'password';
        toggleBtn.textContent = 'T';
    }
}
function toggleManage(){
    const container=document.getElementById('manage_container');
    const button=document.getElementById('manage_btn');
    if(container.style.display==='none'){container.style.display='block';button.value='닫기';}
    else{container.style.display='none';button.value='manage';}
}

function toggleManageContainer() {
    var container = document.getElementById("manage_container");
    if (!container) return;

    // 현재 display 상태가 none이면 보이게, 보이고 있으면 숨김 처리
    if (container.style.display === "none" || container.style.display === "") {
        container.style.display = "block";
    } else {
        container.style.display = "none";
    }
}

function doubleConfirm() {
    if (!confirm("정말 전체 데이터를 초기화하시겠습니까?")) return false;
    if (!confirm("이 작업은 되돌릴 수 없습니다. 계속 진행할까요?")) return false;
    location.href = "/inc/rent_createtb";
    return false;
}

function login() {
    var f = document.getElementById("frm_login");
    if (f.u_id.value.trim() === "") { 
        alert("ID를 입력하세요."); 
        f.u_id.focus(); 
        return false; 
    }
    if (f.u_pw.value.trim() === "") { 
        alert("PW를 입력하세요."); 
        f.u_pw.focus(); 
        return false; // 👈 return false로 통일
    }
    f.action = "/rent_write?f_type=check_id";
    f.submit();
}

function user_logout() {
    if (confirm("로그아웃을 할까요?")) {
        const f = document.getElementById("frm_login");
        f.action = "/rent_write?f_type=log_out";
        f.submit();            
    }
}

function go_print() {
    window.open("/inc/rent_house_print_form", "print_window", "width=900, height=1200, scrollbars=yes");
}


//룸정보등록 스크립트모음---------------------------

	//frmsub.btn_add.enabled = true;
    window.addEventListener('load', () => {
    document.querySelectorAll('input.money').forEach(input => {
        localStorage.removeItem(input.name);
    });
});

function room_add(vv) {
		var frmsub = document.frm_rent_info;

		var obj = frmsub.opt_house;
		if (obj.value == "선택") {
			alert("주택이름을 선택하세요");
			obj.focus();
			return;
		}

		if (!(vv == "edit")) {
			var obj = frmsub.opt_num;
			if (obj.value == "선택") {
				alert("임대룸의 번호를 선택하세요");
				obj.focus();
				return;
			}
		}

		var obj = frmsub.rooms_type;
		if (obj.value == "") {
			alert("임대룸의 타입을 선택하세요");
			obj.focus();
			return;
		}

		var obj = frmsub.p_room_bo;
		if (obj.value == "") {
			alert("보증금 금액을  입력하세요");
			obj.focus();
			return;
		}

		var obj = frmsub.p_room_month_won;
		if (obj.value == "") {
			alert("월 임대료를  입력하세요");
			obj.focus();
			return;
		}

		if (vv == "edit") {
			if (!confirm(frmsub.opt_house.value + "[" + frmsub.r_num.value + "] 을(를) 수정 할까요?")) {
				return;
			}
			frmsub.action = "/rent_write?p=2&f_type=room_edit";
		} else {
			if (!confirm(frmsub.opt_house.value + "[" + frmsub.opt_num.value + "] 을(를) 등록 할까요?")) {
				return;
			}
           // f.action = "/rent_write?f_type=check_id";
			frmsub.action = "/rent_write?p=1&f_type=room_add";
		}
		frmsub.btn_edit.style.backgroundColor = "#E7E7E7";
		frmsub.submit();
	}

	function del_house_room(house_name, room_num, id_num) {
		var temp = "/rent_write?p=1&f_type=house_room_delete&id_num=" + id_num;
		if (!confirm(house_name + "[" + room_num + "] 을(를) 정말삭제  할까요?")) {
			return;
		}
		location.href = temp;
	}

	function room_cancel() {
		var f = document.frm_rent_info;
		var obj = f.opt_house;
		//document.getElementById(obj.value).style.visibility = "hidden";
        f.reset();
		f.opt_house.value = "선택";
	    f.btn_edit.style.backgroundColor = "#E7E7E7";
		//f.btn_rent_info.value = "    등록    ";
		f.btn_add.disabled = false;
	    f.btn_edit.disabled = true;
		
	}

	function room_delete(house_name, pr_name) {
		document.getElementsByName("btn_room_delete").value = house_name + " 삭제";
		alert(pr_name + "삭제합니다.");
		var obj = document.getElementById("room_delete");
		obj.style.width = 100;
		obj.style.left = event.clientX - 55;
		obj.style.top = event.clientY + 5;
		obj.style.visibility = "visible";
	}

	function rent_roomnumber_click(
    id_num,
    h_house,
    room_num,
    p_room_type,
    p_room_month_won,
    p_room_bo,
    p_room_option
) {
    var frmsub = document.querySelector('form[name="frm_rent_info"]');

    //alert("월 임대료를 rent_roomnumber_click 입력하세요");

    // 1. 폼 존재 확인
    if (!frmsub) {
        console.warn("frm_rent_info 폼을 찾을 수 없습니다.");
        return;
    }

    // 2. 주택 선택
    var sel = frmsub.opt_house || document.querySelector('[name="opt_house"]');
    var val = h_house;

    if (sel) {
        if (!sel.querySelector(`option[value="${val}"]`)) {
            sel.add(new Option(val, val));
        }

        sel.value = val;

        if (typeof setSelectedHouse === 'function') {
            setSelectedHouse(sel, h_house);
        }
    }

    // 3. 호수
    if (frmsub.opt_num) {
        frmsub.opt_num.value = room_num;

        if (typeof setSelectedHouse === 'function') {
            setSelectedHouse(frmsub.opt_num, room_num);
        }
    }

    if (frmsub.r_num) {
        frmsub.r_num.value = room_num;
    }

    // 4. 방 타입
    if (frmsub.rooms_type && typeof setSelectedHouse === 'function') {
        setSelectedHouse(frmsub.rooms_type, p_room_type);
    }

    // 5. 기본 정보
    if (frmsub.id_num) {
        frmsub.id_num.value = id_num;
    }

    if (frmsub.p_room_month_won) {
        frmsub.p_room_month_won.value = p_room_month_won;
    }

    if (frmsub.p_room_bo) {
        frmsub.p_room_bo.value = p_room_bo;
    }


    // =====================================================
    // 6. 저장되어 있는 옵션을 체크박스에 반영
    // =====================================================

    console.log("전달받은 p_room_option =", p_room_option);

    var savedOptions = [];

    if (p_room_option) {
        savedOptions = p_room_option
            .split(',')
            .map(function(value) {
                return value.trim();
            });
    }

    console.log("저장된 옵션 배열 =", savedOptions);


    // 모든 옵션 체크박스 가져오기
    var optionCheckboxes =
        document.querySelectorAll('input[name^="ck["]');

    console.log("찾은 체크박스 개수 =", optionCheckboxes.length);


    // 체크박스 전체를 ROOM_OPTION 순서대로 확인
    optionCheckboxes.forEach(function(checkbox, index) {

        if (savedOptions.includes(String(index))) {
            checkbox.checked = true;

            console.log(
                "옵션 " + index + " 체크"
            );

        } else {
            checkbox.checked = false;
        }

    });


    // 7. 버튼 제어
    if (frmsub.btn_edit) {
        frmsub.btn_edit.style.backgroundColor = "#FFBB00";
        frmsub.btn_edit.disabled = false;
    }

    if (frmsub.btn_add) {
        frmsub.btn_add.disabled = true;
    }

    // 8. reload
    if (typeof reload === 'function') {
        // reload(p_room_option);
    }
}


function setSelectedHouse(selectObj, house_name) {
    for (let i = 0; i < selectObj.options.length; i++) {
        if (selectObj.options[i].value === house_name) {
            selectObj.options[i].selected = true;
            break;
        }
    }
}


//==============================================================
//renter_add
//=============================================================
function showPopup(houseName) {
    // 1. URL 설정 (한글 깨짐 방지 인코딩 포함)
    var url = "/rent_house_print_form.php?tenant_name=" + encodeURIComponent(houseName);
    
    // 2. 새 창 띄우기 (window.open 방식)
    var newWindow = window.open(
        url, 
        "print_window", 
        "width=900, height=1200, toolbar=no, menubar=no, location=no, status=no, scrollbars=yes, resizable=yes"
    );

    // 3. 팝업 차단 확인 및 포커스
    if (newWindow) {
        newWindow.focus();
        console.log( houseName + " 창을 성공적으로 열었습니다.");
    } else {
        alert("팝업이 차단되었습니다. 브라우저 설정에서 팝업을 허용해주세요.");
    }
}
function renter_roomnumber_click(h_house, room_num,pr_name, pr_address,pr_email, pr_phone, pr_number) {
    // 값 할당 (모든 필드를 getElementsByName 사용)
	var f = document.querySelector("form[name='frm_renter_add']");
    var sel = f.opt_house;
    var val =h_house;
    if (!sel.querySelector(`option[value="${val}"]`)) {    sel.add(new Option(val, val));}
    sel.value = val;

     f.house_name.value = h_house;
	 f.opt_house.value = h_house;
     f.opt_num.value = room_num;
     f.room_num.value = room_num;
     f.txt_renter_name.value = pr_name;
     f.txt_renter_address.value = pr_address;   
     f.txt_renter_email.value = pr_email;   
	 f.txt_renter_phone.value = pr_phone;

    var pnum1 = pr_number ? pr_number.substring(0, 6) : "";
    var pnum2 = pr_number && pr_number.length > 6 ? pr_number.substring(6, 13) : "";
     f.txt_renter_pnum1.value = pnum1;
     f.txt_renter_pnum2.value = pnum2;
     f.frm_renter_add;
	 f.renter_edit.style.backgroundColor = "#FFBB00";
     f.renter_edit.disabled = false;  // 버튼 활성화
	 f.renter_add.disabled = true;
   
}


function closePopup() {
    var modal = document.getElementById('popup_layer');
    var overlay = document.getElementById('popup_overlay');
    
    if (modal) modal.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
}

 
window.onload = function () {
    var btn = document.getElementsByName("renter_edit")[0];
    if (btn) {
      btn.disabled = true;
    }
  };

function house_onchange(h_house) {
    // select 값 변경
    const select = document.querySelector("select[name='opt_house']");
    if (select) {
        select.value = h_house;
    }

    alert(h_house + " 로 관리대상물이 변경되었습니다.");

    // 현재 URL 가져오기
    const url = new URL(window.location.href);

    // 기존 p 값 유지
    const currentP = url.searchParams.get("p") || "1";

    // 파라미터 변경
    url.searchParams.set("p", currentP);
    url.searchParams.set("house_name", h_house);

    // 페이지 새로고침
    window.location.href = url.toString();
}

function rent_private_submit() {
    var frm = document.frm_renter_add;

    // 필수 입력 체크
    if (frm.opt_house.value === "선택") {
        alert("주택이름을 입력하세요");
        frm.opt_house.focus();
        return false;
    }
    if (frm.opt_num.value === "선택") {
        alert("임대할 방 번호를 선택하세요");
        frm.opt_num.focus();
        return false;
    }
    if (frm.txt_renter_name.value.trim() === "") {
        alert("임차인 이름을 입력하세요");
        frm.txt_renter_name.focus();
        return false;
    }
    if (frm.txt_renter_address.value.trim() === "") {
        alert("임차인 주소를 입력하세요");
        frm.txt_renter_address.focus();
        return false;
    }

    // 이메일 체크
    if (!isValidEmail(frm.txt_renter_email.value)) {
        var result = confirm("임차인 E-mail 주소가 정확하지 않습니다. 다시 입력하시겠습니까?");
        if (result) {
            frm.txt_renter_email.focus();
            return false; // 폼 제출 중단
        }
        // 취소(Cancel) → 그냥 넘어가서 제출
    }

    // 전화번호 체크
    if (frm.txt_renter_phone.value.trim() === "") {
        alert("임차인 전화번호를 입력하세요");
        frm.txt_renter_phone.focus();
        return false;
    }

    // 주민번호 체크
    if (frm.txt_renter_pnum1.value.trim() === "" || frm.txt_renter_pnum2.value.trim() === "") {
        alert("임차인 주민번호를 입력하세요");
        if (frm.txt_renter_pnum1.value.trim() === "") {
            frm.txt_renter_pnum1.focus();
        } else {
            frm.txt_renter_pnum2.focus();
        }
        return false;
    }

    // 모든 체크 통과 → 폼 제출
//	 frm.renter_cancel.style.backgroundColor = "#E7E7E7";
    frm.action = "/rent_write?p=3&f_type=renter_add";
    frm.submit();
    return true;
}

// onclick=\"rent_roomnumber_click('{$house_name}', '{$room_num}', '{$pr_name}', '{$pr_phone}', '{$pr_rent_start}')
 
 

function isValidEmail(email) {
    var regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email.trim());
}


function delete_room(room_num, pr_name) {
    if (!confirm(pr_name + "을 정말 삭제 할까요?")) return;
    location.href = "/rent_write?p=3&f_type=room_delete&room_num=" + encodeURIComponent(room_num) + "&pr_name=" + encodeURIComponent(pr_name);
}

function room_renter_edit_onclick() {
	if (document.getElementsByName("house_name")[0])
      house_name=    document.getElementsByName("house_name")[0].value;

    if (document.getElementsByName("room_num")[0])
      room_num= document.getElementsByName("room_num")[0].value ;
	
    if (!confirm(house_name+" 의 "+room_num + "호를  정말 수정 할까요?")) return;
	var frm = document.frm_renter_add;
	 frm.renter_cancel.style.backgroundColor = "#E7E7E7";
     frm.submit();
}

function cancel() {
    var f = document.querySelector("form[name='frm_renter_add']");
    f.renter_edit.style.backgroundColor = "#E7E7E7";
	f.renter_add.disabled = false;
	f.renter_edit.disabled = true;
    f.reset();
}
//=================================================================


function reload(p_room_option) {
    console.log("함수 실행됨! 넘어온 값:", p_room_option); // 개발자 도구 확인용

    // 1. 모든 체크박스부터 일단 싹 끄기 (초기화)
    var allCks = document.querySelectorAll('input[name^="ck["]');
    for (var j = 0; j < allCks.length; j++) {
        allCks[j].checked = false;
    }

    // 2. 넘어온 값이 없으면 여기서 종료
    if (!p_room_option || p_room_option === "") {
        return;
    }

    // 3. 값 배열로 만들기
    var selectedOptions = p_room_option.split(',').map(function (item) {
        return item.trim();
    });

    // 4. 하나씩 돌면서 체크하기
    for (var i = 0; i < allCks.length; i++) {
        // name 속성에서 숫자만 추출 (ck[0] -> 0)
        var nameStr = allCks[i].getAttribute('name'); 
        var index = nameStr.substring(nameStr.indexOf("[") + 1, nameStr.indexOf("]"));

        // 포함되어 있으면 체크
        if (selectedOptions.indexOf(index) !== -1) {
            allCks[i].checked = true;
        }
    }
}

 // =========================
    // 5?? 금액 포맷
    // =========================
   document.querySelectorAll('input.money').forEach(input => {
    // 1. 초기 로드: 값을 가져온 뒤 바로 콤마 포맷팅 적용
    const storedValue = localStorage.getItem(input.name);
    if (storedValue) {
        let cleanNum = storedValue.replace(/\D/g, '');
        if (cleanNum) input.value = Number(cleanNum).toLocaleString('ko-KR');
    }

    // 2. 입력 중: 실시간 저장 (선택 사항)
    input.addEventListener('input', () => { 
        localStorage.setItem(input.name, input.value.replace(/\D/g, '')); 
    });

    // 3. 포커스 얻음: 콤마 제거해서 숫자만 보이게
    input.addEventListener('focus', () => {
        input.value = input.value.replace(/,/g, '');
    });

    // 4. 포커스 잃음: 콤마 추가 및 깔끔하게 숫자만 저장
    input.addEventListener('blur', () => {
        let num = input.value.replace(/\D/g, '');
        if (num) {
            input.value = Number(num).toLocaleString('ko-KR');
            localStorage.setItem(input.name, num); // 콤마 없는 순수 숫자 저장 추천
        }
    });
});


	function select_option(obj, value) {
		var ff = obj.options.length - 1;

		for (i = 1; i < ff; i++) {
			ov = obj[i].value;
			if (ov == value) {
				obj[i].selected = true;
				
                alert(obj[i].name+"체크박스를 선택했습니다 수정버튼을 눌러!!");

			}
		}
	}

	function check_box(obj, value) {
		alert(value);
		var a = [value];
		var value_arr = new Array(value);
		var ff = value_arr.length;
		alert(ff);
		for (i = 1; i < ff; i++) {
			ov = obj[i].value;
			alert(ov + value);
			if (ov == value) {
				obj[i].checked;
			}
		}
	}

	function fncChk(input_str, type_sw) {
		var fm = input_str;
		switch (type_sw) {
			case 1:
				ptn = /[^\d]/;
				if (fm.search(ptn) != -1) alert('숫자만 입력 가능 합니다.');
				break;
			case 2:
				ptn = /\d/;
				if (fm.search(ptn) != -1) alert('문자만 입력 가능 합니다.');
				break;
		}
	}
