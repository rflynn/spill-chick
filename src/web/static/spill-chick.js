
var isOpera = navigator.userAgent.indexOf("Opera") > -1;
var isIE = navigator.userAgent.indexOf("MSIE") > 1 && !isOpera;
var isMoz = navigator.userAgent.indexOf("Mozilla/5.") == 0 && !isOpera;

function textboxSelect(oTextbox, iStart, iEnd)
{
	switch(arguments.length)
	{
	case 1:
		oTextbox.select();
		break;
	case 2:
		iEnd = oTextbox.value.length;
		/* falls through */
	case 3:
		if (isIE)
		{
			var oRange = oTextbox.createTextRange();
			oRange.moveStart("character", iStart);
			oRange.moveEnd("character", - oTextbox.value.length + iEnd);
			oRange.select();
		}
		else if (isMoz)
		{
			oTextbox.setSelectionRange(iStart, iEnd);
		}
	}
}
