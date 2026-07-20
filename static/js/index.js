const $ = (id) => document.getElementById(id);

let moduleStyle = 'rounded';
document.querySelectorAll('#module_style input[name="module_style"]').forEach(input => {
  input.addEventListener('change', () => {
    moduleStyle = input.dataset.v;
    render();
  });
});

$('fg_color').addEventListener('input', e => $('fg_color_val').textContent = e.target.value);
$('fg_color2').addEventListener('input', e => $('fg_color2_val').textContent = e.target.value);
$('bg_color').addEventListener('input', e => $('bg_color_val').textContent = e.target.value);
$('logo_size_ratio').addEventListener('input', e => $('logo_size_val').textContent = e.target.value + '%');

$('use_gradient').addEventListener('change', e => {
  const show = e.target.checked;
  $('fg_color2_wrap').classList.toggle('d-none', !show);
  $('gradient_dir_wrap').classList.toggle('d-none', !show);
});

let lastImageDataUrl = null;
let debounceTimer = null;

function scheduleRender(){
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(render, 400);
}

['data','fg_color','fg_color2','bg_color','transparent_bg','rounded_logo',
 'logo_size_ratio','box_size','border','error_correction','gradient','use_gradient']
 .forEach(id => {
   const el = $(id);
   const evt = (el.tagName === 'SELECT' || el.type === 'checkbox') ? 'change' : 'input';
   el.addEventListener(evt, scheduleRender);
 });
$('logo').addEventListener('change', () => {
  const file = $('logo').files[0];
  $('logo_options').classList.toggle('d-none', !file);
  if (file) $('logo_filename').textContent = file.name;
  render();
});

$('removeLogoBtn').addEventListener('click', () => {
  $('logo').value = '';
  $('logo_options').classList.add('d-none');
  render();
});
 $('refreshBtn').addEventListener('click', render);

async function render(){
  const status = $('status');
  status.textContent = 'генерируем…';

  const fd = new FormData();
  fd.append('data', $('data').value || ' ');
  fd.append('module_style', moduleStyle);
  fd.append('fg_color', $('fg_color').value);
  fd.append('fg_color2', $('use_gradient').checked ? $('fg_color2').value : '');
  fd.append('gradient', $('gradient').value);
  fd.append('bg_color', $('transparent_bg').checked ? 'transparent' : $('bg_color').value);
  fd.append('box_size', $('box_size').value);
  fd.append('border', $('border').value);
  fd.append('error_correction', $('error_correction').value);
  fd.append('logo_size_ratio', ($('logo_size_ratio').value / 100).toString());
  fd.append('rounded_logo', $('rounded_logo').checked);
  if ($('logo').files[0]) fd.append('logo', $('logo').files[0]);

  try{
    const res = await fetch('/generate-base64', { method:'POST', body: fd });
    if(!res.ok){
      const err = await res.json().catch(()=>({detail:'Ошибка генерации'}));
      throw new Error(err.detail || 'Ошибка генерации');
    }
    const json = await res.json();
    lastImageDataUrl = json.image;

    const swatch = $('swatch');
    swatch.innerHTML = '';
    const img = document.createElement('img');
    img.src = lastImageDataUrl;
    swatch.appendChild(img);

    if ($('transparent_bg').checked) {
      swatch.style.background =
        'linear-gradient(45deg, #2b2a27 25%, transparent 25%) -10px 0/20px 20px,' +
        'linear-gradient(-45deg, #2b2a27 25%, transparent 25%) -10px 0/20px 20px,' +
        'linear-gradient(45deg, transparent 75%, #2b2a27 75%) -10px 0/20px 20px,' +
        'linear-gradient(-45deg, transparent 75%, #2b2a27 75%) -10px 0/20px 20px,' +
        'var(--bs-tertiary-bg)';
    } else {
      swatch.style.background = $('bg_color').value;
    }

    $('downloadBtn').href = lastImageDataUrl;
    status.textContent = 'готово';
  }catch(e){
    status.textContent = 'ошибка: ' + e.message;
  }
}

render();
