
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
		if (oTextbox.createTextRange)
		{
			var oRange = oTextbox.createTextRange();
			oRange.moveStart("character", iStart);
			oRange.moveEnd("character", - oTextbox.value.length + iEnd);
			oRange.select();
			oTextbox.scrollTop = oRange.boundingTop
		}
		else if (oTextbox.setSelectionRange)
		{
			oTextbox.setSelectionRange(iStart, iEnd);
		}
	}
}
